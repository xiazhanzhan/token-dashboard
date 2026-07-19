from __future__ import annotations

import sqlite3

from app.collectors.hermes import HermesCollector


def execute_source(path, sql, params=()):
    conn = sqlite3.connect(path)
    conn.execute(sql, params)
    conn.commit()
    conn.close()


def test_hermes_baseline_delta_reset_and_read_only(database, settings):
    execute_source(
        settings.hermes_database_path,
        """
        INSERT INTO sessions (
            id, started_at, model, input_tokens, cache_read_tokens,
            cache_write_tokens, output_tokens, reasoning_tokens
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        ("h-1", 1767225600, "deepseek-test", 100, 50, 0, 20, 5),
    )
    collector = HermesCollector(
        database, settings.hermes_database_path, settings.timezone
    )
    with database.transaction() as conn:
        first = collector.collect(conn)
    assert first["events_added"] == 1
    with database.connect() as conn:
        row = conn.execute("SELECT * FROM usage_events").fetchone()
    assert row["total_tokens"] == 170
    assert row["reasoning_tokens"] == 5

    execute_source(
        settings.hermes_database_path,
        """
        UPDATE sessions SET input_tokens = 150, cache_read_tokens = 70,
                            output_tokens = 30, reasoning_tokens = 8
        WHERE id = 'h-1'
        """,
    )
    with database.transaction() as conn:
        second = collector.collect(conn)
    assert second["events_added"] == 1
    with database.connect() as conn:
        assert conn.execute("SELECT SUM(total_tokens) FROM usage_events").fetchone()[0] == 250

    with database.transaction() as conn:
        repeat = collector.collect(conn)
    assert repeat["events_added"] == 0

    execute_source(
        settings.hermes_database_path,
        """
        UPDATE sessions SET input_tokens = 10, cache_read_tokens = 2,
                            output_tokens = 5, reasoning_tokens = 2
        WHERE id = 'h-1'
        """,
    )
    with database.transaction() as conn:
        reset = collector.collect(conn)
    assert reset["resets"] == 1
    assert reset["events_added"] == 1
    with database.connect() as conn:
        rows = conn.execute("SELECT * FROM usage_events").fetchall()
    assert len(rows) == 1
    assert rows[0]["total_tokens"] == 17
