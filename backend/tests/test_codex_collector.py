from __future__ import annotations

import json
from pathlib import Path

from app.collectors.codex import CodexCollector


def write_records(path: Path, records: list[object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        for record in records:
            if isinstance(record, str):
                handle.write(record + "\n")
            else:
                handle.write(json.dumps(record) + "\n")


def token_event(timestamp: str, input_tokens: int, cached: int, output: int, reasoning: int = 0):
    return {
        "timestamp": timestamp,
        "type": "event_msg",
        "payload": {
            "type": "token_count",
            "info": {
                "total_token_usage": {
                    "input_tokens": input_tokens,
                    "cached_input_tokens": cached,
                    "output_tokens": output,
                    "reasoning_output_tokens": reasoning,
                    "total_tokens": input_tokens + output,
                }
            },
        },
    }


def test_codex_delta_cache_model_reset_and_idempotence(database, settings):
    path = settings.codex_home / "sessions" / "2026" / "01" / "01" / (
        "rollout-2026-01-01T00-00-00-11111111-2222-3333-4444-555555555555.jsonl"
    )
    records = [
        {
            "timestamp": "2026-01-01T00:00:00Z",
            "type": "session_meta",
            "payload": {"id": "session-a"},
        },
        {
            "timestamp": "2026-01-01T00:00:00Z",
            "type": "turn_context",
            "payload": {"model": "gpt-a"},
        },
        token_event("2026-01-01T00:00:01Z", 100, 40, 10, 3),
        # Context-only indicator: total changes in last usage but cumulative values do not.
        token_event("2026-01-01T00:00:02Z", 100, 40, 10, 3),
        "{malformed json",
        token_event("2026-01-01T00:00:03Z", 180, 80, 30, 8),
        {
            "timestamp": "2026-01-01T00:00:04Z",
            "type": "turn_context",
            "payload": {"model": "gpt-b"},
        },
        # Cumulative counter reset; current values become the new delta.
        token_event("2026-01-01T00:00:05Z", 20, 0, 5, 2),
    ]
    write_records(path, records)
    collector = CodexCollector(database, settings.codex_home, settings.timezone)

    with database.transaction() as conn:
        result = collector.collect(conn)
    assert result["events_added"] == 3
    assert result["malformed_lines"] == 1

    with database.connect() as conn:
        rows = conn.execute(
            "SELECT * FROM usage_events ORDER BY occurred_at"
        ).fetchall()
    assert [row["model"] for row in rows] == ["gpt-a", "gpt-a", "gpt-b"]
    assert (rows[0]["input_tokens"], rows[0]["cache_read_tokens"], rows[0]["output_tokens"]) == (60, 40, 10)
    assert (rows[1]["input_tokens"], rows[1]["cache_read_tokens"], rows[1]["output_tokens"]) == (40, 40, 20)
    assert rows[2]["total_tokens"] == 25
    assert sum(row["total_tokens"] for row in rows) == 235
    assert all(
        row["total_tokens"]
        == row["input_tokens"]
        + row["cache_read_tokens"]
        + row["cache_write_tokens"]
        + row["output_tokens"]
        for row in rows
    )

    with database.transaction() as conn:
        repeat = collector.collect(conn)
    assert repeat["events_added"] == 0

    write_records(path, [token_event("2026-01-01T00:00:06Z", 35, 5, 9, 3)])
    with database.transaction() as conn:
        appended = collector.collect(conn)
    assert appended["events_added"] == 1
    with database.connect() as conn:
        assert conn.execute("SELECT COUNT(*) FROM usage_events").fetchone()[0] == 4


def test_codex_incomplete_line_is_retried(database, settings):
    path = settings.codex_home / "sessions" / "active.jsonl"
    path.write_bytes(b'{"type":"session_meta","payload":{"id":"active"}}')
    collector = CodexCollector(database, settings.codex_home, settings.timezone)
    with database.transaction() as conn:
        collector.collect(conn)
        cursor = database.get_cursor(conn, "codex", str(path))
    assert cursor is not None
    assert cursor["byte_offset"] == 0

    with path.open("ab") as handle:
        handle.write(b"\n")
    write_records(path, [token_event("2026-01-02T00:00:00Z", 10, 0, 2)])
    with database.transaction() as conn:
        result = collector.collect(conn)
    assert result["events_added"] == 1


def test_codex_forked_history_is_not_counted_twice(database, settings):
    path = settings.codex_home / "sessions" / "forked.jsonl"
    write_records(
        path,
        [
            {
                "timestamp": "2026-07-19T00:00:00Z",
                "type": "session_meta",
                "payload": {
                    "id": "child-session",
                    "forked_from_id": "parent-session",
                    "parent_thread_id": "parent-session",
                    "thread_source": "subagent",
                },
            },
            # Copied parent history. It advances the child's cumulative
            # baseline but must not become a second usage event.
            token_event("2026-07-19T00:00:01Z", 1_000, 600, 100, 25),
            token_event("2026-07-19T00:00:02Z", 1_500, 900, 150, 35),
            {
                "timestamp": "2026-07-19T00:00:03Z",
                "type": "turn_context",
                "payload": {"model": "gpt-child"},
            },
            # Only the child's new delta should be stored.
            token_event("2026-07-19T00:00:04Z", 1_700, 1_000, 190, 45),
        ],
    )
    collector = CodexCollector(database, settings.codex_home, settings.timezone)

    with database.transaction() as conn:
        result = collector.collect(conn)
    assert result["events_added"] == 1

    with database.connect() as conn:
        rows = conn.execute("SELECT * FROM usage_events").fetchall()
    assert len(rows) == 1
    assert rows[0]["model"] == "gpt-child"
    assert rows[0]["input_tokens"] == 100
    assert rows[0]["cache_read_tokens"] == 100
    assert rows[0]["output_tokens"] == 40
    assert rows[0]["reasoning_tokens"] == 10
    assert rows[0]["total_tokens"] == 240

    with database.transaction() as conn:
        repeat = collector.collect(conn)
    assert repeat["events_added"] == 0
