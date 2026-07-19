from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path
from typing import Any, Dict, List
from zoneinfo import ZoneInfo

from ..database import Database
from .common import SourceUnavailable, make_event, parse_timestamp, stable_id


TOTAL_KEYS = (
    "input_tokens",
    "cached_input_tokens",
    "output_tokens",
    "reasoning_output_tokens",
)


class CodexCollector:
    def __init__(self, database: Database, codex_home: Path, timezone: ZoneInfo):
        self.database = database
        self.codex_home = Path(codex_home)
        self.timezone = timezone

    def discover_files(self) -> List[Path]:
        roots = [
            self.codex_home / "sessions",
            self.codex_home / "archived_sessions",
        ]
        files: List[Path] = []
        for root in roots:
            if root.exists():
                files.extend(path for path in root.rglob("*.jsonl") if path.is_file())
        return sorted(set(files))

    def collect(self, conn: sqlite3.Connection) -> Dict[str, int]:
        if not self.codex_home.exists():
            raise SourceUnavailable(f"Codex 目录不存在：{self.codex_home}")
        files = self.discover_files()
        if not files:
            raise SourceUnavailable("未找到 Codex JSONL 会话文件")

        # A rewritten/truncated active file invalidates cumulative counters.
        # Rebuild all Codex-derived events so cross-file de-duplication remains correct.
        rebuild = False
        for path in files:
            stat = path.stat()
            cursor = self.database.get_cursor(conn, "codex", str(path))
            if cursor and (
                cursor.get("inode") != stat.st_ino
                or stat.st_size < int(cursor.get("byte_offset") or 0)
            ):
                rebuild = True
                break
        if rebuild:
            # A local source rewrite must never erase events received from
            # other computers by the central dashboard.
            conn.execute(
                "DELETE FROM usage_events WHERE source = 'codex' AND device_id = 'local'"
            )
            conn.execute("DELETE FROM source_cursors WHERE source = 'codex'")

        stats = {
            "files": len(files),
            "events_added": 0,
            "events_seen": 0,
            "malformed_lines": 0,
            "rebuilds": int(rebuild),
        }
        for path in files:
            result = self._collect_file(conn, path)
            for key, value in result.items():
                stats[key] = stats.get(key, 0) + value
        return stats

    def _collect_file(
        self, conn: sqlite3.Connection, path: Path
    ) -> Dict[str, int]:
        stat = path.stat()
        source_key = str(path)
        cursor = self.database.get_cursor(conn, "codex", source_key)
        state: Dict[str, Any] = dict((cursor or {}).get("state") or {})
        offset = int((cursor or {}).get("byte_offset") or 0)
        if not cursor:
            state = {
                "session_id": self._session_id_from_filename(path),
                "model": "unknown",
                "totals": {key: 0 for key in TOTAL_KEYS},
                "line_number": 0,
                "skip_fork_history": False,
            }

        result = {"events_added": 0, "events_seen": 0, "malformed_lines": 0}
        with path.open("rb") as handle:
            handle.seek(offset)
            while True:
                line_start = handle.tell()
                raw = handle.readline()
                if not raw:
                    break
                # Do not consume an incomplete line that an active session is still writing.
                if not raw.endswith(b"\n"):
                    handle.seek(line_start)
                    break
                state["line_number"] = int(state.get("line_number") or 0) + 1
                try:
                    record = json.loads(raw.decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError):
                    result["malformed_lines"] += 1
                    continue
                self._handle_record(conn, record, state, source_key, result, stat.st_mtime)
            next_offset = handle.tell()

        latest = path.stat()
        self.database.save_cursor(
            conn,
            source="codex",
            source_key=source_key,
            inode=latest.st_ino,
            byte_offset=next_offset,
            file_size=latest.st_size,
            file_mtime=latest.st_mtime,
            state=state,
        )
        return result

    def _handle_record(
        self,
        conn: sqlite3.Connection,
        record: Dict[str, Any],
        state: Dict[str, Any],
        source_key: str,
        result: Dict[str, int],
        fallback_time: float,
    ) -> None:
        payload = record.get("payload")
        if not isinstance(payload, dict):
            payload = {}
        record_type = record.get("type")
        if record_type == "session_meta":
            state["session_id"] = str(payload.get("id") or state.get("session_id"))
            # Forked/sub-agent rollouts can begin with a replay of the parent
            # thread. Those token_count rows are historical copies, not new
            # usage. Keep advancing their cumulative counters, but do not emit
            # events until the child receives its first model-bearing context.
            state["skip_fork_history"] = bool(
                payload.get("forked_from_id") or payload.get("parent_thread_id")
            )
            return
        if record_type == "turn_context":
            if payload.get("model"):
                state["model"] = str(payload["model"])
                state["skip_fork_history"] = False
            return
        if record_type != "event_msg" or payload.get("type") != "token_count":
            return

        info = payload.get("info")
        if not isinstance(info, dict):
            return
        totals = info.get("total_token_usage")
        if not isinstance(totals, dict):
            return
        current = {key: self._non_negative_int(totals.get(key)) for key in TOTAL_KEYS}
        previous_raw = state.get("totals")
        previous = (
            {key: self._non_negative_int(previous_raw.get(key)) for key in TOTAL_KEYS}
            if isinstance(previous_raw, dict)
            else {key: 0 for key in TOTAL_KEYS}
        )
        reset = any(current[key] < previous[key] for key in TOTAL_KEYS)
        delta = (
            current
            if reset
            else {key: current[key] - previous[key] for key in TOTAL_KEYS}
        )
        state["totals"] = current

        if state.get("skip_fork_history"):
            return

        # Component-less token_count rows are context indicators and do not
        # advance cumulative billable usage. They must not inflate totals.
        if delta["input_tokens"] == 0 and delta["output_tokens"] == 0:
            return

        cached = min(delta["cached_input_tokens"], delta["input_tokens"])
        uncached = delta["input_tokens"] - cached
        reasoning = min(delta["reasoning_output_tokens"], delta["output_tokens"])
        occurred_at = parse_timestamp(record.get("timestamp"), fallback_time)
        session_id = str(state.get("session_id") or "unknown")
        model = str(state.get("model") or "unknown")
        event_id = stable_id(
            "codex",
            session_id,
            record.get("timestamp"),
            *(current[key] for key in TOTAL_KEYS),
        )
        event = make_event(
            event_id=event_id,
            source="codex",
            source_key=source_key,
            session_id=session_id,
            occurred_at=occurred_at,
            tz=self.timezone,
            model=model,
            input_tokens=uncached,
            cache_read_tokens=cached,
            cache_write_tokens=0,
            output_tokens=delta["output_tokens"],
            reasoning_tokens=reasoning,
            metadata={"counter_reset": reset},
        )
        result["events_seen"] += 1
        if self.database.insert_event(conn, event):
            result["events_added"] += 1

    @staticmethod
    def _non_negative_int(value: Any) -> int:
        try:
            return max(0, int(value or 0))
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _session_id_from_filename(path: Path) -> str:
        stem = path.stem
        match = re.search(
            r"([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})$",
            stem,
        )
        if match:
            return match.group(1)
        return stem
