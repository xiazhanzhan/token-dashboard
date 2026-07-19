from __future__ import annotations

import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, Tuple
from zoneinfo import ZoneInfo

from ..database import Database
from .common import SourceUnavailable, make_event, stable_id


COUNTER_COLUMNS = (
    "input_tokens",
    "cache_read_tokens",
    "cache_write_tokens",
    "output_tokens",
    "reasoning_tokens",
)


class HermesCollector:
    def __init__(
        self, database: Database, hermes_database_path: Path, timezone: ZoneInfo
    ):
        self.database = database
        self.hermes_database_path = Path(hermes_database_path)
        self.timezone = timezone

    def collect(self, conn: sqlite3.Connection) -> Dict[str, int]:
        if not self.hermes_database_path.exists():
            raise SourceUnavailable(
                f"Hermes 数据库不存在：{self.hermes_database_path}"
            )
        source = self._open_source()
        try:
            rows = source.execute(
                """
                SELECT id, started_at, COALESCE(model, 'unknown') AS model,
                       COALESCE(input_tokens, 0) AS input_tokens,
                       COALESCE(cache_read_tokens, 0) AS cache_read_tokens,
                       COALESCE(cache_write_tokens, 0) AS cache_write_tokens,
                       COALESCE(output_tokens, 0) AS output_tokens,
                       COALESCE(reasoning_tokens, 0) AS reasoning_tokens
                FROM sessions
                ORDER BY started_at, id
                """
            ).fetchall()
        except sqlite3.Error as exc:
            raise SourceUnavailable(f"Hermes 数据库读取失败：{exc}") from exc
        finally:
            source.close()

        result = {
            "sessions": len(rows),
            "events_added": 0,
            "events_seen": 0,
            "resets": 0,
        }
        observed_at = time.time()
        for row in rows:
            inserted, reset = self._merge_session(conn, dict(row), observed_at)
            result["events_seen"] += int(inserted or reset)
            result["events_added"] += int(inserted)
            result["resets"] += int(reset)
        return result

    def _open_source(self) -> sqlite3.Connection:
        # mode=ro preserves Hermes' WAL visibility while guaranteeing no writes.
        uri = self.hermes_database_path.resolve().as_uri() + "?mode=ro"
        connection = sqlite3.connect(uri, uri=True, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA query_only=ON")
        connection.execute("PRAGMA busy_timeout=10000")
        return connection

    def _merge_session(
        self, conn: sqlite3.Connection, row: Dict[str, Any], observed_at: float
    ) -> Tuple[bool, bool]:
        session_id = str(row.get("id") or "unknown")
        model = str(row.get("model") or "unknown")
        started_at = float(row.get("started_at") or observed_at)
        current = {name: self._counter(row.get(name)) for name in COUNTER_COLUMNS}
        previous_row = conn.execute(
            "SELECT * FROM hermes_sessions WHERE session_id = ?", (session_id,)
        ).fetchone()
        previous = dict(previous_row) if previous_row is not None else None
        generation_number = int(previous.get("generation") or 0) if previous else 0
        reset = bool(
            previous
            and any(current[name] < int(previous[name]) for name in COUNTER_COLUMNS)
        )
        if reset:
            deleted_ids = [
                str(item["id"])
                for item in conn.execute(
                    """
                    SELECT id FROM usage_events
                    WHERE source = 'hermes' AND external_session_id = ?
                      AND device_id = 'local'
                    """,
                    (session_id,),
                ).fetchall()
            ]
            if deleted_ids:
                conn.executemany(
                    "DELETE FROM agent_delivery WHERE event_id = ?",
                    [(event_id,) for event_id in deleted_ids],
                )
            conn.execute(
                """
                DELETE FROM usage_events
                WHERE source = 'hermes' AND external_session_id = ?
                  AND device_id = 'local'
                """,
                (session_id,),
            )
            generation_number += 1
            previous = None

        if previous is None:
            delta = current
            occurred_at = started_at
            generation = f"baseline-{generation_number}"
        else:
            delta = {
                name: current[name] - int(previous[name]) for name in COUNTER_COLUMNS
            }
            occurred_at = observed_at
            generation = (
                f"{generation_number}-"
                + stable_id(*(current[name] for name in COUNTER_COLUMNS))[:16]
            )

        inserted = False
        if delta["input_tokens"] or delta["cache_read_tokens"] or delta[
            "cache_write_tokens"
        ] or delta["output_tokens"]:
            event_id = stable_id("hermes", session_id, generation)
            event = make_event(
                event_id=event_id,
                source="hermes",
                source_key=str(self.hermes_database_path),
                session_id=session_id,
                occurred_at=occurred_at,
                tz=self.timezone,
                model=model,
                input_tokens=delta["input_tokens"],
                cache_read_tokens=delta["cache_read_tokens"],
                cache_write_tokens=delta["cache_write_tokens"],
                output_tokens=delta["output_tokens"],
                reasoning_tokens=delta["reasoning_tokens"],
                metadata={
                    "baseline": previous is None,
                    "counter_reset": reset,
                    "replace_session": reset,
                    "generation": generation_number,
                },
            )
            inserted = self.database.insert_event(conn, event)

        conn.execute(
            """
            INSERT INTO hermes_sessions (
                session_id, generation, started_at, model, input_tokens, cache_read_tokens,
                cache_write_tokens, output_tokens, reasoning_tokens, last_seen_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(session_id) DO UPDATE SET
                generation = excluded.generation,
                started_at = excluded.started_at,
                model = excluded.model,
                input_tokens = excluded.input_tokens,
                cache_read_tokens = excluded.cache_read_tokens,
                cache_write_tokens = excluded.cache_write_tokens,
                output_tokens = excluded.output_tokens,
                reasoning_tokens = excluded.reasoning_tokens,
                last_seen_at = excluded.last_seen_at
            """,
            (
                session_id,
                generation_number,
                started_at,
                model,
                current["input_tokens"],
                current["cache_read_tokens"],
                current["cache_write_tokens"],
                current["output_tokens"],
                current["reasoning_tokens"],
                observed_at,
            ),
        )
        return inserted, reset

    @staticmethod
    def _counter(value: Any) -> int:
        try:
            return max(0, int(value or 0))
        except (TypeError, ValueError):
            return 0
