"""Export only Hermes session token counters from WSL into a local SQLite file."""

from __future__ import annotations

import os
import sqlite3
import sys
from pathlib import Path
from urllib.parse import quote


def expression(columns: set[str], name: str, fallback: str = "0") -> str:
    if name not in columns:
        return f"{fallback} AS {name}"
    return f"COALESCE({name}, {fallback}) AS {name}"


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("usage: wsl-hermes-export.py SOURCE_STATE_DB DESTINATION_DB")
    source_path = Path(sys.argv[1]).expanduser().resolve()
    destination = Path(sys.argv[2])
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    temporary.unlink(missing_ok=True)

    source_uri = f"file:{quote(str(source_path))}?mode=ro"
    source = sqlite3.connect(source_uri, uri=True, timeout=10)
    source.row_factory = sqlite3.Row
    source.execute("PRAGMA query_only=ON")
    source.execute("PRAGMA busy_timeout=10000")
    try:
        columns = {
            str(row[1])
            for row in source.execute("PRAGMA table_info(sessions)").fetchall()
        }
        if "id" not in columns:
            raise RuntimeError(f"sessions table is missing from {source_path}")
        started = "started_at" if "started_at" in columns else "created_at"
        if started not in columns:
            started_expression = "0 AS started_at"
        else:
            started_expression = f"COALESCE({started}, 0) AS started_at"
        select = ", ".join(
            [
                "id",
                started_expression,
                expression(columns, "model", "'unknown'"),
                expression(columns, "input_tokens"),
                expression(columns, "cache_read_tokens"),
                expression(columns, "cache_write_tokens"),
                expression(columns, "output_tokens"),
                expression(columns, "reasoning_tokens"),
            ]
        )
        rows = source.execute(f"SELECT {select} FROM sessions").fetchall()
    finally:
        source.close()

    target = sqlite3.connect(str(temporary))
    try:
        target.execute(
            """
            CREATE TABLE sessions (
                id TEXT PRIMARY KEY,
                started_at REAL,
                model TEXT,
                input_tokens INTEGER,
                cache_read_tokens INTEGER,
                cache_write_tokens INTEGER,
                output_tokens INTEGER,
                reasoning_tokens INTEGER
            )
            """
        )
        target.executemany(
            """
            INSERT INTO sessions VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [tuple(row) for row in rows],
        )
        target.commit()
    finally:
        target.close()
    os.replace(temporary, destination)
    print(f"exported {len(rows)} Hermes sessions from {source_path}")


if __name__ == "__main__":
    main()
