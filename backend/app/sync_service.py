from __future__ import annotations

import sqlite3
import threading
import time
from datetime import date, datetime, timedelta
from typing import Any, Dict, Optional

from .collectors import CodexCollector, HermesCollector
from .collectors.common import SourceUnavailable
from .config import Settings
from .database import Database


class SyncService:
    def __init__(self, database: Database, settings: Settings):
        self.database = database
        self.settings = settings
        self.codex = CodexCollector(database, settings.codex_home, settings.timezone)
        self.hermes = HermesCollector(
            database, settings.hermes_database_path, settings.timezone
        )
        self._lock = threading.Lock()

    def sync_all(self) -> Dict[str, Any]:
        if not self.settings.collect_local:
            return {
                "status": "remote_only",
                "message": "中心主机由设备采集端上报，本机直读已关闭",
                "eventsAdded": {"codex": 0, "hermes": 0},
            }
        if not self._lock.acquire(blocking=False):
            return {"status": "busy", "message": "同步任务已在运行"}
        started_at = time.time()
        with self.database.transaction() as conn:
            run_id = conn.execute(
                "INSERT INTO sync_runs (started_at, status) VALUES (?, 'running')",
                (started_at,),
            ).lastrowid

        results: Dict[str, Any] = {}
        errors: Dict[str, str] = {}
        added = {"codex": 0, "hermes": 0}
        try:
            for source, collector in (("codex", self.codex), ("hermes", self.hermes)):
                try:
                    with self.database.transaction() as conn:
                        source_result = collector.collect(conn)
                        records_seen = int(
                            source_result.get("events_seen")
                            or source_result.get("sessions")
                            or 0
                        )
                        self.database.set_source_status(
                            conn,
                            source,
                            available=True,
                            records_seen=records_seen,
                            error=None,
                        )
                    results[source] = source_result
                    added[source] = int(source_result.get("events_added") or 0)
                except (SourceUnavailable, sqlite3.Error, OSError, ValueError) as exc:
                    message = str(exc)[:500]
                    errors[source] = message
                    with self.database.transaction() as conn:
                        self.database.set_source_status(
                            conn, source, available=False, error=message
                        )

            if not errors:
                status = "completed"
            elif len(errors) == 1:
                status = "partial"
            else:
                status = "error"
            completed_at = time.time()
            with self.database.transaction() as conn:
                conn.execute(
                    """
                    UPDATE devices
                    SET last_seen_at = ?, updated_at = ?
                    WHERE id = 'local'
                    """,
                    (completed_at, completed_at),
                )
                conn.execute(
                    """
                    UPDATE sync_runs SET
                        completed_at = ?, status = ?, codex_events_added = ?,
                        hermes_events_added = ?, error = ?
                    WHERE id = ?
                    """,
                    (
                        completed_at,
                        status,
                        added["codex"],
                        added["hermes"],
                        "; ".join(f"{key}: {value}" for key, value in errors.items())
                        or None,
                        run_id,
                    ),
                )
            return {
                "status": status,
                "runId": run_id,
                "startedAt": started_at,
                "completedAt": completed_at,
                "eventsAdded": added,
                "sources": results,
                "errors": errors,
            }
        except Exception as exc:
            message = str(exc)[:500]
            with self.database.transaction() as conn:
                conn.execute(
                    "UPDATE sync_runs SET completed_at = ?, status = 'error', error = ? WHERE id = ?",
                    (time.time(), message, run_id),
                )
            raise
        finally:
            self._lock.release()

    def capture_snapshot(self, snapshot_day: Optional[str] = None) -> Dict[str, Any]:
        if snapshot_day is None:
            snapshot_day = (
                datetime.now(self.settings.timezone).date() - timedelta(days=1)
            ).isoformat()
        try:
            parsed = date.fromisoformat(snapshot_day)
        except ValueError as exc:
            raise ValueError("快照日期必须为 YYYY-MM-DD") from exc
        day = parsed.isoformat()
        captured_at = time.time()
        with self.database.transaction() as conn:
            rows = conn.execute(
                """
                SELECT source, model,
                       SUM(input_tokens) AS input_tokens,
                       SUM(cache_read_tokens) AS cache_read_tokens,
                       SUM(cache_write_tokens) AS cache_write_tokens,
                       SUM(output_tokens) AS output_tokens,
                       SUM(reasoning_tokens) AS reasoning_tokens,
                       SUM(total_tokens) AS total_tokens,
                       COUNT(*) AS event_count
                FROM usage_events
                WHERE local_day = ?
                GROUP BY source, model
                """,
                (day,),
            ).fetchall()
            conn.execute("DELETE FROM daily_snapshots WHERE snapshot_day = ?", (day,))
            conn.executemany(
                """
                INSERT INTO daily_snapshots (
                    snapshot_day, source, model, input_tokens,
                    cache_read_tokens, cache_write_tokens, output_tokens,
                    reasoning_tokens, total_tokens, event_count, captured_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        day,
                        row["source"],
                        row["model"],
                        row["input_tokens"] or 0,
                        row["cache_read_tokens"] or 0,
                        row["cache_write_tokens"] or 0,
                        row["output_tokens"] or 0,
                        row["reasoning_tokens"] or 0,
                        row["total_tokens"] or 0,
                        row["event_count"] or 0,
                        captured_at,
                    )
                    for row in rows
                ],
            )
        return {"snapshotDay": day, "rows": len(rows), "capturedAt": captured_at}

    def capture_missing_snapshots(self) -> Dict[str, Any]:
        yesterday = datetime.now(self.settings.timezone).date() - timedelta(days=1)
        with self.database.connect() as conn:
            days = [
                row[0]
                for row in conn.execute(
                    """
                    SELECT DISTINCT local_day FROM usage_events
                    WHERE local_day <= ?
                      AND local_day NOT IN (
                          SELECT DISTINCT snapshot_day FROM daily_snapshots
                      )
                    ORDER BY local_day
                    """,
                    (yesterday.isoformat(),),
                ).fetchall()
            ]
        for day in days:
            self.capture_snapshot(day)
        return {"capturedDays": days, "count": len(days)}
