from __future__ import annotations

import time
from datetime import datetime, timedelta

from app.analytics import AnalyticsService
from app.collectors.common import make_event, stable_id
from app.sync_service import SyncService


def add_event(database, settings, *, source, day, model, input_tokens, cache, output, reasoning=0):
    timestamp = datetime.fromisoformat(f"{day}T12:00:00+08:00").timestamp()
    event = make_event(
        event_id=stable_id(source, day, model, input_tokens, cache, output),
        source=source,
        source_key="fixture",
        session_id=f"{source}-{day}-{model}",
        occurred_at=timestamp,
        tz=settings.timezone,
        model=model,
        input_tokens=input_tokens,
        cache_read_tokens=cache,
        cache_write_tokens=0,
        output_tokens=output,
        reasoning_tokens=reasoning,
        metadata={},
    )
    with database.transaction() as conn:
        database.insert_event(conn, event)


def test_timeseries_zero_fill_filters_and_total_invariant(database, settings):
    add_event(database, settings, source="codex", day="2024-02-29", model="gpt-x", input_tokens=10, cache=20, output=5, reasoning=2)
    add_event(database, settings, source="hermes", day="2024-03-02", model="deep-x", input_tokens=3, cache=7, output=2)
    analytics = AnalyticsService(database, settings)

    result = analytics.timeseries("day", "2024-02-28", "2024-03-02")
    assert result["buckets"] == ["2024-02-28", "2024-02-29", "2024-03-01", "2024-03-02"]
    assert len(result["points"]) == 8
    codex = next(point for point in result["points"] if point["bucket"] == "2024-02-29" and point["source"] == "codex")
    assert codex["totalTokens"] == 35
    assert codex["reasoningTokens"] == 2
    assert codex["totalTokens"] == codex["inputTokens"] + codex["cacheReadTokens"] + codex["cacheWriteTokens"] + codex["outputTokens"]

    filtered = analytics.timeseries("day", "2024-02-28", "2024-03-02", source="hermes")
    assert {point["source"] for point in filtered["points"]} == {"hermes"}
    assert sum(point["totalTokens"] for point in filtered["points"]) == 12

    model_filtered = analytics.timeseries("month", "2024-01-01", "2024-03-31", model="gpt-x")
    assert sum(point["totalTokens"] for point in model_filtered["points"]) == 35


def test_summary_calendar_models_sessions_and_snapshot_idempotence(database, settings):
    today = datetime.now(settings.timezone).date()
    add_event(database, settings, source="codex", day=today.isoformat(), model="gpt-x", input_tokens=10, cache=5, output=2)
    add_event(database, settings, source="hermes", day=today.isoformat(), model="deep-x", input_tokens=20, cache=10, output=4)
    analytics = AnalyticsService(database, settings)

    summary = analytics.summary()
    assert summary["periods"]["today"]["current"]["totalTokens"] == 51
    assert summary["periods"]["today"]["bySource"]["codex"]["totalTokens"] == 17
    models = analytics.models(today.isoformat(), today.isoformat())
    assert [item["model"] for item in models["models"]] == ["deep-x", "gpt-x"]
    calendar = analytics.calendar(today.year)
    assert calendar["days"][0]["totalTokens"] == 51
    sessions = analytics.sessions(limit=10)
    assert sessions["total"] == 2

    service = SyncService(database, settings)
    first = service.capture_snapshot(today.isoformat())
    second = service.capture_snapshot(today.isoformat())
    assert first["rows"] == second["rows"] == 2
    with database.connect() as conn:
        assert conn.execute(
            "SELECT COUNT(*) FROM daily_snapshots WHERE snapshot_day = ?",
            (today.isoformat(),),
        ).fetchone()[0] == 2
