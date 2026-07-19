from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime, timezone
from typing import Any, Dict
from zoneinfo import ZoneInfo


class SourceUnavailable(RuntimeError):
    pass


def stable_id(*parts: Any) -> str:
    payload = json.dumps(parts, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def parse_timestamp(value: Any, fallback: float) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str) and value:
        try:
            normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
            parsed = datetime.fromisoformat(normalized)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.timestamp()
        except ValueError:
            pass
    return fallback


def local_day(timestamp: float, tz: ZoneInfo) -> str:
    return datetime.fromtimestamp(timestamp, tz=tz).date().isoformat()


def make_event(
    *,
    event_id: str,
    source: str,
    source_key: str,
    session_id: str,
    occurred_at: float,
    tz: ZoneInfo,
    model: str,
    input_tokens: int,
    cache_read_tokens: int,
    cache_write_tokens: int,
    output_tokens: int,
    reasoning_tokens: int,
    metadata: Dict[str, Any],
) -> Dict[str, Any]:
    input_tokens = max(0, int(input_tokens))
    cache_read_tokens = max(0, int(cache_read_tokens))
    cache_write_tokens = max(0, int(cache_write_tokens))
    output_tokens = max(0, int(output_tokens))
    reasoning_tokens = max(0, min(int(reasoning_tokens), output_tokens))
    return {
        "id": event_id,
        "source": source,
        "source_key": source_key,
        "external_session_id": session_id or "unknown",
        "occurred_at": occurred_at,
        "local_day": local_day(occurred_at, tz),
        "model": model or "unknown",
        "input_tokens": input_tokens,
        "cache_read_tokens": cache_read_tokens,
        "cache_write_tokens": cache_write_tokens,
        "output_tokens": output_tokens,
        "reasoning_tokens": reasoning_tokens,
        "total_tokens": (
            input_tokens + cache_read_tokens + cache_write_tokens + output_tokens
        ),
        "metadata_json": json.dumps(
            metadata, ensure_ascii=False, separators=(",", ":"), sort_keys=True
        ),
        "created_at": time.time(),
    }
