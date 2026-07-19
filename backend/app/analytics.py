from __future__ import annotations

import calendar
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from .config import Settings
from .database import Database


TOKEN_COLUMNS = (
    "input_tokens",
    "cache_read_tokens",
    "cache_write_tokens",
    "output_tokens",
    "reasoning_tokens",
    "total_tokens",
)


def empty_totals() -> Dict[str, int]:
    return {
        "inputTokens": 0,
        "cacheReadTokens": 0,
        "cacheWriteTokens": 0,
        "outputTokens": 0,
        "reasoningTokens": 0,
        "totalTokens": 0,
    }


def row_totals(row: Any) -> Dict[str, int]:
    return {
        "inputTokens": int(row["input_tokens"] or 0),
        "cacheReadTokens": int(row["cache_read_tokens"] or 0),
        "cacheWriteTokens": int(row["cache_write_tokens"] or 0),
        "outputTokens": int(row["output_tokens"] or 0),
        "reasoningTokens": int(row["reasoning_tokens"] or 0),
        "totalTokens": int(row["total_tokens"] or 0),
    }


class AnalyticsService:
    def __init__(self, database: Database, settings: Settings):
        self.database = database
        self.settings = settings

    def summary(
        self,
        source: str = "all",
        model: Optional[str] = None,
        device: str = "all",
        account: str = "all",
    ) -> Dict[str, Any]:
        today = datetime.now(self.settings.timezone).date()
        periods = {
            "today": (today, today, today - timedelta(days=1), today - timedelta(days=1)),
            "week": self._period_to_date(today, "week"),
            "month": self._period_to_date(today, "month"),
            "year": self._period_to_date(today, "year"),
        }
        response: Dict[str, Any] = {}
        with self.database.connect() as conn:
            for key, (current_start, current_end, previous_start, previous_end) in periods.items():
                current = self._sum_range(
                    conn, current_start, current_end, source=source, model=model,
                    device=device, account=account,
                )
                previous = self._sum_range(
                    conn, previous_start, previous_end, source=source, model=model,
                    device=device, account=account,
                )
                previous_total = previous["totals"]["totalTokens"]
                current_total = current["totals"]["totalTokens"]
                change = (
                    (current_total - previous_total) / previous_total * 100
                    if previous_total > 0
                    else None
                )
                response[key] = {
                    "start": current_start.isoformat(),
                    "end": current_end.isoformat(),
                    "current": current["totals"],
                    "bySource": current["bySource"],
                    "previous": previous["totals"],
                    "changePercent": change,
                }

        return {
            "generatedAt": datetime.now(self.settings.timezone).isoformat(),
            "timezone": self.settings.timezone_name,
            "periods": response,
        }

    def timeseries(
        self,
        granularity: str = "day",
        from_day: Optional[str] = None,
        to_day: Optional[str] = None,
        source: str = "all",
        model: Optional[str] = None,
        device: str = "all",
        account: str = "all",
    ) -> Dict[str, Any]:
        if granularity not in {"day", "week", "month", "year"}:
            raise ValueError("granularity 必须是 day/week/month/year")
        start, end = self._resolve_range(granularity, from_day, to_day)
        conditions, params = self._filters(
            start, end, source, model, device=device, account=account
        )
        with self.database.connect() as conn:
            rows = conn.execute(
                f"""
                SELECT local_day, source,
                       SUM(input_tokens) AS input_tokens,
                       SUM(cache_read_tokens) AS cache_read_tokens,
                       SUM(cache_write_tokens) AS cache_write_tokens,
                       SUM(output_tokens) AS output_tokens,
                       SUM(reasoning_tokens) AS reasoning_tokens,
                       SUM(total_tokens) AS total_tokens
                FROM usage_events
                WHERE {' AND '.join(conditions)}
                GROUP BY local_day, source
                ORDER BY local_day, source
                """,
                params,
            ).fetchall()

        buckets = self._bucket_sequence(start, end, granularity)
        sources = [source] if source in {"codex", "hermes"} else ["codex", "hermes"]
        aggregated: Dict[Tuple[str, str], Dict[str, int]] = {
            (bucket, item_source): empty_totals()
            for bucket in buckets
            for item_source in sources
        }
        for row in rows:
            bucket = self._bucket_for_day(date.fromisoformat(row["local_day"]), granularity)
            key = (bucket, row["source"])
            if key not in aggregated:
                continue
            values = row_totals(row)
            for name, value in values.items():
                aggregated[key][name] += value

        points = [
            {"bucket": bucket, "source": item_source, **aggregated[(bucket, item_source)]}
            for bucket in buckets
            for item_source in sources
        ]
        return {
            "granularity": granularity,
            "from": start.isoformat(),
            "to": end.isoformat(),
            "timezone": self.settings.timezone_name,
            "buckets": buckets,
            "points": points,
        }

    def models(
        self,
        from_day: Optional[str] = None,
        to_day: Optional[str] = None,
        source: str = "all",
        limit: int = 50,
        device: str = "all",
        account: str = "all",
    ) -> Dict[str, Any]:
        today = datetime.now(self.settings.timezone).date()
        start = date.fromisoformat(from_day) if from_day else date(today.year, 1, 1)
        end = date.fromisoformat(to_day) if to_day else today
        conditions, params = self._filters(
            start, end, source, None, device=device, account=account
        )
        with self.database.connect() as conn:
            rows = conn.execute(
                f"""
                SELECT model, source,
                       COUNT(DISTINCT device_id || ':' || external_session_id) AS sessions,
                       SUM(input_tokens) AS input_tokens,
                       SUM(cache_read_tokens) AS cache_read_tokens,
                       SUM(cache_write_tokens) AS cache_write_tokens,
                       SUM(output_tokens) AS output_tokens,
                       SUM(reasoning_tokens) AS reasoning_tokens,
                       SUM(total_tokens) AS total_tokens
                FROM usage_events
                WHERE {' AND '.join(conditions)}
                GROUP BY model, source
                ORDER BY total_tokens DESC
                """,
                params,
            ).fetchall()

        by_model: Dict[str, Dict[str, Any]] = {}
        for row in rows:
            item = by_model.setdefault(
                row["model"],
                {
                    "model": row["model"],
                    **empty_totals(),
                    "sessions": 0,
                    "sourceBreakdown": {},
                },
            )
            values = row_totals(row)
            for key, value in values.items():
                item[key] += value
            item["sessions"] += int(row["sessions"] or 0)
            item["sourceBreakdown"][row["source"]] = values["totalTokens"]
        items = sorted(
            by_model.values(), key=lambda item: item["totalTokens"], reverse=True
        )[: max(1, min(limit, 200))]
        return {"from": start.isoformat(), "to": end.isoformat(), "models": items}

    def calendar(
        self,
        year: int,
        source: str = "all",
        model: Optional[str] = None,
        device: str = "all",
        account: str = "all",
    ) -> Dict[str, Any]:
        if year < 2000 or year > 2200:
            raise ValueError("year 超出支持范围")
        start, end = date(year, 1, 1), date(year, 12, 31)
        conditions, params = self._filters(
            start, end, source, model, device=device, account=account
        )
        with self.database.connect() as conn:
            rows = conn.execute(
                f"""
                SELECT local_day, source, SUM(total_tokens) AS total_tokens
                FROM usage_events
                WHERE {' AND '.join(conditions)}
                GROUP BY local_day, source
                ORDER BY local_day
                """,
                params,
            ).fetchall()
        daily: Dict[str, Dict[str, int]] = {}
        for row in rows:
            item = daily.setdefault(
                row["local_day"],
                {"day": row["local_day"], "totalTokens": 0, "codexTokens": 0, "hermesTokens": 0},
            )
            total = int(row["total_tokens"] or 0)
            item["totalTokens"] += total
            item[f"{row['source']}Tokens"] += total
        return {"year": year, "days": list(daily.values())}

    def sessions(
        self,
        source: str = "all",
        model: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
        sort: str = "latest",
        device: str = "all",
        account: str = "all",
    ) -> Dict[str, Any]:
        conditions = ["1 = 1"]
        params: List[Any] = []
        if source in {"codex", "hermes"}:
            conditions.append("source = ?")
            params.append(source)
        if model and model != "all":
            conditions.append("model = ?")
            params.append(model)
        if device and device != "all":
            conditions.append("device_id = ?")
            params.append(device)
        if account and account != "all":
            conditions.append("account_id = ?")
            params.append(account)
        where = " AND ".join(conditions)
        order = "last_activity DESC" if sort == "latest" else "total_tokens DESC"
        with self.database.connect() as conn:
            total = conn.execute(
                f"""
                SELECT COUNT(*) FROM (
                    SELECT 1 FROM usage_events WHERE {where}
                    GROUP BY device_id, account_id, source, external_session_id, model
                )
                """,
                params,
            ).fetchone()[0]
            rows = conn.execute(
                f"""
                SELECT source, external_session_id, model, device_id, account_id,
                       COALESCE((SELECT name FROM devices d WHERE d.id = usage_events.device_id), device_id) AS device_name,
                       COALESCE((SELECT label FROM accounts a WHERE a.id = usage_events.account_id), account_id) AS account_label,
                       MIN(occurred_at) AS started_at,
                       MAX(occurred_at) AS last_activity,
                       COUNT(*) AS event_count,
                       SUM(input_tokens) AS input_tokens,
                       SUM(cache_read_tokens) AS cache_read_tokens,
                       SUM(cache_write_tokens) AS cache_write_tokens,
                       SUM(output_tokens) AS output_tokens,
                       SUM(reasoning_tokens) AS reasoning_tokens,
                       SUM(total_tokens) AS total_tokens
                FROM usage_events
                WHERE {where}
                GROUP BY device_id, account_id, source, external_session_id, model
                ORDER BY {order}
                LIMIT ? OFFSET ?
                """,
                [*params, max(1, min(limit, 200)), max(0, offset)],
            ).fetchall()
        return {
            "total": int(total),
            "limit": limit,
            "offset": offset,
            "sessions": [
                {
                    "source": row["source"],
                    "sessionId": row["external_session_id"],
                    "model": row["model"],
                    "deviceId": row["device_id"],
                    "deviceName": row["device_name"],
                    "accountId": row["account_id"],
                    "accountLabel": row["account_label"],
                    "startedAt": row["started_at"],
                    "lastActivity": row["last_activity"],
                    "eventCount": int(row["event_count"] or 0),
                    **row_totals(row),
                }
                for row in rows
            ],
        }

    def _sum_range(
        self,
        conn: Any,
        start: date,
        end: date,
        *,
        source: str,
        model: Optional[str],
        device: str = "all",
        account: str = "all",
    ) -> Dict[str, Any]:
        conditions, params = self._filters(
            start, end, source, model, device=device, account=account
        )
        rows = conn.execute(
            f"""
            SELECT source,
                   SUM(input_tokens) AS input_tokens,
                   SUM(cache_read_tokens) AS cache_read_tokens,
                   SUM(cache_write_tokens) AS cache_write_tokens,
                   SUM(output_tokens) AS output_tokens,
                   SUM(reasoning_tokens) AS reasoning_tokens,
                   SUM(total_tokens) AS total_tokens
            FROM usage_events
            WHERE {' AND '.join(conditions)}
            GROUP BY source
            """,
            params,
        ).fetchall()
        totals = empty_totals()
        by_source = {"codex": empty_totals(), "hermes": empty_totals()}
        for row in rows:
            values = row_totals(row)
            by_source[row["source"]] = values
            for name, value in values.items():
                totals[name] += value
        return {"totals": totals, "bySource": by_source}

    @staticmethod
    def _filters(
        start: date,
        end: date,
        source: str,
        model: Optional[str],
        *,
        device: str = "all",
        account: str = "all",
    ) -> Tuple[List[str], List[Any]]:
        if start > end:
            raise ValueError("开始日期不能晚于结束日期")
        conditions = ["local_day BETWEEN ? AND ?"]
        params: List[Any] = [start.isoformat(), end.isoformat()]
        if source in {"codex", "hermes"}:
            conditions.append("source = ?")
            params.append(source)
        elif source != "all":
            raise ValueError("source 必须是 all/codex/hermes")
        if model and model != "all":
            conditions.append("model = ?")
            params.append(model)
        if device and device != "all":
            conditions.append("device_id = ?")
            params.append(device)
        if account and account != "all":
            conditions.append("account_id = ?")
            params.append(account)
        return conditions, params

    def _resolve_range(
        self, granularity: str, from_day: Optional[str], to_day: Optional[str]
    ) -> Tuple[date, date]:
        today = datetime.now(self.settings.timezone).date()
        end = date.fromisoformat(to_day) if to_day else today
        if from_day:
            start = date.fromisoformat(from_day)
        elif granularity == "day":
            start = end - timedelta(days=29)
        elif granularity == "week":
            start = end - timedelta(days=end.weekday() + 25 * 7)
        elif granularity == "month":
            start = self._shift_month(date(end.year, end.month, 1), -23)
        else:
            start = date(max(2000, end.year - 4), 1, 1)
            with self.database.connect() as conn:
                earliest = conn.execute("SELECT MIN(local_day) FROM usage_events").fetchone()[0]
            if earliest:
                start = max(start, date(int(str(earliest)[:4]), 1, 1))
        if start > end:
            raise ValueError("开始日期不能晚于结束日期")
        return start, end

    @staticmethod
    def _period_to_date(today: date, period: str) -> Tuple[date, date, date, date]:
        if period == "week":
            current_start = today - timedelta(days=today.weekday())
            previous_start = current_start - timedelta(days=7)
            previous_end = previous_start + timedelta(days=today.weekday())
        elif period == "month":
            current_start = date(today.year, today.month, 1)
            previous_month_start = AnalyticsService._shift_month(current_start, -1)
            previous_last = calendar.monthrange(
                previous_month_start.year, previous_month_start.month
            )[1]
            previous_start = previous_month_start
            previous_end = date(
                previous_month_start.year,
                previous_month_start.month,
                min(today.day, previous_last),
            )
        elif period == "year":
            current_start = date(today.year, 1, 1)
            previous_start = date(today.year - 1, 1, 1)
            try:
                previous_end = today.replace(year=today.year - 1)
            except ValueError:
                previous_end = date(today.year - 1, 2, 28)
        else:
            raise ValueError("未知周期")
        return current_start, today, previous_start, previous_end

    def _bucket_sequence(self, start: date, end: date, granularity: str) -> List[str]:
        values: List[str] = []
        current = start
        if granularity == "week":
            current -= timedelta(days=current.weekday())
        elif granularity == "month":
            current = date(current.year, current.month, 1)
        elif granularity == "year":
            current = date(current.year, 1, 1)
        while current <= end:
            values.append(self._bucket_for_day(current, granularity))
            if granularity == "day":
                current += timedelta(days=1)
            elif granularity == "week":
                current += timedelta(days=7)
            elif granularity == "month":
                current = self._shift_month(current, 1)
            else:
                current = date(current.year + 1, 1, 1)
        return values

    @staticmethod
    def _bucket_for_day(day: date, granularity: str) -> str:
        if granularity == "day":
            return day.isoformat()
        if granularity == "week":
            return (day - timedelta(days=day.weekday())).isoformat()
        if granularity == "month":
            return f"{day.year:04d}-{day.month:02d}"
        return f"{day.year:04d}"

    @staticmethod
    def _shift_month(value: date, count: int) -> date:
        absolute = value.year * 12 + (value.month - 1) + count
        year, month_index = divmod(absolute, 12)
        day = min(value.day, calendar.monthrange(year, month_index + 1)[1])
        return date(year, month_index + 1, day)
