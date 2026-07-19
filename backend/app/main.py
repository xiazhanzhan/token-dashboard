from __future__ import annotations

import asyncio
import contextlib
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator, Optional

from fastapi import FastAPI, Header, HTTPException, Query, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .analytics import AnalyticsService
from .config import Settings
from .database import Database
from .ingest import IngestService
from .schemas import IngestRequest
from .sync_service import SyncService


def create_app(settings: Optional[Settings] = None) -> FastAPI:
    settings = settings or Settings.from_env()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    database = Database(settings.database_path)
    database.initialize()
    sync_service = SyncService(database, settings)
    analytics = AnalyticsService(database, settings)
    ingest_service = IngestService(database, settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        await asyncio.to_thread(sync_service.sync_all)
        await asyncio.to_thread(sync_service.capture_missing_snapshots)
        stop = asyncio.Event()

        async def periodic_sync() -> None:
            while not stop.is_set():
                try:
                    await asyncio.wait_for(
                        stop.wait(), timeout=settings.sync_interval_seconds
                    )
                except asyncio.TimeoutError:
                    await asyncio.to_thread(sync_service.sync_all)

        task = asyncio.create_task(periodic_sync(), name="token-dashboard-sync")
        try:
            yield
        finally:
            stop.set()
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task

    app = FastAPI(
        title="Codex + Hermes Token Dashboard",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.state.database = database
    app.state.sync_service = sync_service
    app.state.analytics = analytics
    app.state.ingest_service = ingest_service

    @app.middleware("http")
    async def response_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.get("/api/health")
    def health():
        with database.connect() as conn:
            if settings.collect_local:
                source_rows = conn.execute(
                    "SELECT * FROM source_status ORDER BY source"
                ).fetchall()
                last_run = conn.execute(
                    "SELECT * FROM sync_runs ORDER BY id DESC LIMIT 1"
                ).fetchone()
            else:
                source_rows = conn.execute(
                    """
                    SELECT source, 1 AS available,
                           MAX(created_at) AS last_success_at,
                           NULL AS last_error, COUNT(*) AS records_seen,
                           MAX(created_at) AS updated_at
                    FROM usage_events
                    GROUP BY source
                    ORDER BY source
                    """
                ).fetchall()
                latest_ingest = conn.execute(
                    """
                    SELECT received_at, inserted_count, duplicate_count
                    FROM ingest_batches ORDER BY received_at DESC LIMIT 1
                    """
                ).fetchone()
                last_run = (
                    {
                        "id": 0,
                        "started_at": latest_ingest["received_at"],
                        "completed_at": latest_ingest["received_at"],
                        "status": "ingested",
                        "error": None,
                    }
                    if latest_ingest is not None
                    else None
                )
            event_counts = {
                row["source"]: int(row["count"])
                for row in conn.execute(
                    "SELECT source, COUNT(*) AS count FROM usage_events GROUP BY source"
                ).fetchall()
            }
        sources = {
            source: {
                "available": False,
                "lastSuccessAt": None,
                "lastError": (
                    "尚未收到采集端数据"
                    if not settings.collect_local
                    else "尚未同步"
                ),
                "recordsSeen": 0,
                "events": event_counts.get(source, 0),
            }
            for source in ("codex", "hermes")
        }
        for row in source_rows:
            sources[row["source"]] = {
                "available": bool(row["available"]),
                "lastSuccessAt": row["last_success_at"],
                "lastError": row["last_error"],
                "recordsSeen": int(row["records_seen"] or 0),
                "events": event_counts.get(row["source"], 0),
            }
        available = sum(int(item["available"]) for item in sources.values())
        return {
            "status": "ok" if available == 2 else "partial" if available else "error",
            "timezone": settings.timezone_name,
            "syncIntervalSeconds": settings.sync_interval_seconds,
            "collectionMode": "local" if settings.collect_local else "agents",
            "sources": sources,
            "lastSync": dict(last_run) if last_run else None,
        }

    @app.post("/api/sync")
    async def sync_now():
        return await asyncio.to_thread(sync_service.sync_all)

    @app.get("/api/devices")
    def devices():
        return ingest_service.devices()

    @app.post("/api/v1/ingest/events")
    def ingest_events(
        payload: IngestRequest,
        authorization: Optional[str] = Header(None, max_length=500),
    ):
        prefix = "Bearer "
        token = (
            authorization[len(prefix):].strip()
            if authorization and authorization.startswith(prefix)
            else ""
        )
        try:
            return ingest_service.ingest(token, payload)
        except PermissionError as exc:
            raise HTTPException(status_code=401, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/api/summary")
    def summary(
        source: str = Query("all", pattern="^(all|codex|hermes)$"),
        model: Optional[str] = Query(None, max_length=200),
        device: str = Query("all", max_length=200),
        account: str = Query("all", max_length=200),
    ):
        return analytics.summary(
            source=source, model=model, device=device, account=account
        )

    @app.get("/api/timeseries")
    def timeseries(
        granularity: str = Query("day", pattern="^(day|week|month|year)$"),
        from_day: Optional[str] = Query(None, alias="from", pattern=r"^\d{4}-\d{2}-\d{2}$"),
        to_day: Optional[str] = Query(None, alias="to", pattern=r"^\d{4}-\d{2}-\d{2}$"),
        source: str = Query("all", pattern="^(all|codex|hermes)$"),
        model: Optional[str] = Query(None, max_length=200),
        device: str = Query("all", max_length=200),
        account: str = Query("all", max_length=200),
    ):
        try:
            return analytics.timeseries(
                granularity=granularity,
                from_day=from_day,
                to_day=to_day,
                source=source,
                model=model,
                device=device,
                account=account,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/api/models")
    def models(
        from_day: Optional[str] = Query(None, alias="from", pattern=r"^\d{4}-\d{2}-\d{2}$"),
        to_day: Optional[str] = Query(None, alias="to", pattern=r"^\d{4}-\d{2}-\d{2}$"),
        source: str = Query("all", pattern="^(all|codex|hermes)$"),
        limit: int = Query(50, ge=1, le=200),
        device: str = Query("all", max_length=200),
        account: str = Query("all", max_length=200),
    ):
        try:
            return analytics.models(
                from_day, to_day, source, limit, device=device, account=account
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/api/calendar")
    def calendar_usage(
        year: int = Query(..., ge=2000, le=2200),
        source: str = Query("all", pattern="^(all|codex|hermes)$"),
        model: Optional[str] = Query(None, max_length=200),
        device: str = Query("all", max_length=200),
        account: str = Query("all", max_length=200),
    ):
        try:
            return analytics.calendar(
                year, source, model, device=device, account=account
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/api/sessions")
    def sessions(
        source: str = Query("all", pattern="^(all|codex|hermes)$"),
        model: Optional[str] = Query(None, max_length=200),
        limit: int = Query(20, ge=1, le=200),
        offset: int = Query(0, ge=0),
        sort: str = Query("latest", pattern="^(latest|tokens)$"),
        device: str = Query("all", max_length=200),
        account: str = Query("all", max_length=200),
    ):
        return analytics.sessions(
            source, model, limit, offset, sort, device=device, account=account
        )

    if settings.frontend_dist.exists():
        assets = settings.frontend_dist / "assets"
        if assets.exists():
            app.mount("/assets", StaticFiles(directory=assets), name="assets")

        @app.get("/{full_path:path}", include_in_schema=False)
        def frontend(full_path: str):
            candidate = (settings.frontend_dist / full_path).resolve()
            dist = settings.frontend_dist.resolve()
            if full_path and str(candidate).startswith(str(dist)) and candidate.is_file():
                return FileResponse(candidate)
            return FileResponse(settings.frontend_dist / "index.html")
    else:
        @app.get("/", include_in_schema=False)
        def frontend_missing():
            return JSONResponse(
                {
                    "message": "前端尚未构建，请运行 npm --prefix frontend run build",
                    "docs": "/docs",
                },
                status_code=503,
            )

    return app


app = create_app()
