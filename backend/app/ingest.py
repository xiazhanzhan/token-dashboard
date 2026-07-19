from __future__ import annotations

import hashlib
import sqlite3
import time
from typing import Any, Dict

from .collectors.common import make_event, stable_id
from .config import Settings
from .database import Database
from .schemas import IngestRequest


class IngestService:
    def __init__(self, database: Database, settings: Settings):
        self.database = database
        self.settings = settings

    @staticmethod
    def token_hash(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    @staticmethod
    def normalize_label(label: str) -> str:
        # Windows PowerShell 5 can decode UTF-8 scripts as a legacy code page.
        # Repair the only non-ASCII separator used by the bundled installer.
        return label.replace("Â·", "·").strip()

    def authenticate(self, token: str) -> Dict[str, Any]:
        if not token:
            raise PermissionError("缺少设备认证密钥")
        digest = self.token_hash(token)
        with self.database.connect() as conn:
            row = conn.execute(
                """
                SELECT * FROM devices
                WHERE token_hash = ? AND enabled = 1 AND is_local = 0
                """,
                (digest,),
            ).fetchone()
        if row is None:
            raise PermissionError("设备认证失败或已被吊销")
        return dict(row)

    def ingest(self, token: str, payload: IngestRequest) -> Dict[str, Any]:
        device = self.authenticate(token)
        device_id = str(device["id"])
        now = time.time()
        earliest = 946684800.0  # 2000-01-01 UTC
        latest = now + 86400
        inserted = 0
        duplicates = 0

        with self.database.transaction() as conn:
            existing_batch = conn.execute(
                """
                SELECT * FROM ingest_batches
                WHERE device_id = ? AND batch_id = ?
                """,
                (device_id, payload.batchId),
            ).fetchone()
            if existing_batch is not None:
                conn.execute(
                    "UPDATE devices SET last_seen_at = ?, updated_at = ? WHERE id = ?",
                    (now, now, device_id),
                )
                return {
                    "status": "duplicate_batch",
                    "deviceId": device_id,
                    "batchId": payload.batchId,
                    "received": int(existing_batch["event_count"]),
                    "inserted": int(existing_batch["inserted_count"]),
                    "duplicates": int(existing_batch["duplicate_count"]),
                }

            for item in payload.events:
                if not earliest <= item.occurredAt <= latest:
                    raise ValueError("事件时间超出允许范围")
                if item.replaceSession and item.source != "hermes":
                    raise ValueError("只有 Hermes 会话可以请求权威替换")
                reasoning = min(item.reasoningTokens, item.outputTokens)
                total = (
                    item.inputTokens
                    + item.cacheReadTokens
                    + item.cacheWriteTokens
                    + item.outputTokens
                )
                event = make_event(
                    event_id=stable_id("remote", device_id, item.eventId),
                    source=item.source,
                    source_key=f"remote:{device_id}",
                    session_id=item.sessionHash,
                    occurred_at=item.occurredAt,
                    tz=self.settings.timezone,
                    model=item.model or "unknown",
                    input_tokens=item.inputTokens,
                    cache_read_tokens=item.cacheReadTokens,
                    cache_write_tokens=item.cacheWriteTokens,
                    output_tokens=item.outputTokens,
                    reasoning_tokens=reasoning,
                    metadata={
                        "remote": True,
                        "schema_version": item.schemaVersion,
                        "batch_id": payload.batchId,
                        "client_total": item.totalTokens,
                        "normalized_total": total,
                    },
                )
                account_key = item.accountKey or item.source
                account_id = f"{device_id}:{account_key}"
                existing_account = conn.execute(
                    "SELECT source, label FROM accounts WHERE id = ?",
                    (account_id,),
                ).fetchone()
                if existing_account is not None and existing_account["source"] != item.source:
                    raise ValueError("账号标识与数据来源不一致")
                account_label = (
                    self.normalize_label(item.accountLabel)
                    if item.accountLabel
                    else (
                        str(existing_account["label"])
                        if existing_account is not None
                        else f"{item.source.title()} · {device['name']}"
                    )
                )
                conn.execute(
                    """
                    INSERT INTO accounts (
                        id, device_id, source, label, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        label = excluded.label,
                        updated_at = excluded.updated_at
                    """,
                    (
                        account_id,
                        device_id,
                        item.source,
                        account_label,
                        now,
                        now,
                    ),
                )
                event["device_id"] = device_id
                event["account_id"] = account_id
                if item.replaceSession:
                    stale_days = conn.execute(
                        """
                        SELECT DISTINCT local_day FROM usage_events
                        WHERE device_id = ? AND account_id = ? AND source = ?
                          AND external_session_id = ?
                        """,
                        (device_id, account_id, item.source, item.sessionHash),
                    ).fetchall()
                    conn.execute(
                        """
                        DELETE FROM usage_events
                        WHERE device_id = ? AND account_id = ? AND source = ?
                          AND external_session_id = ?
                        """,
                        (device_id, account_id, item.source, item.sessionHash),
                    )
                    conn.executemany(
                        "DELETE FROM daily_snapshots WHERE snapshot_day = ?",
                        [(row["local_day"],) for row in stale_days],
                    )
                if self.database.insert_event(conn, event):
                    inserted += 1
                    # An offline device may submit history after a daily snapshot
                    # was captured. Mark that day dirty so the next snapshot run
                    # rebuilds it from the authoritative event table.
                    conn.execute(
                        "DELETE FROM daily_snapshots WHERE snapshot_day = ?",
                        (event["local_day"],),
                    )
                else:
                    duplicates += 1

            conn.execute(
                """
                INSERT INTO ingest_batches (
                    device_id, batch_id, received_at, event_count,
                    inserted_count, duplicate_count
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    device_id,
                    payload.batchId,
                    now,
                    len(payload.events),
                    inserted,
                    duplicates,
                ),
            )
            conn.execute(
                "UPDATE devices SET last_seen_at = ?, updated_at = ? WHERE id = ?",
                (now, now, device_id),
            )

        return {
            "status": "ok",
            "deviceId": device_id,
            "batchId": payload.batchId,
            "received": len(payload.events),
            "inserted": inserted,
            "duplicates": duplicates,
        }

    def devices(self) -> Dict[str, Any]:
        with self.database.connect() as conn:
            devices = conn.execute(
                """
                SELECT id, name, platform, enabled, is_local, last_seen_at,
                       created_at, updated_at
                FROM devices
                ORDER BY is_local DESC, name COLLATE NOCASE
                """
            ).fetchall()
            account_rows = conn.execute(
                "SELECT id, device_id, source, label FROM accounts ORDER BY label"
            ).fetchall()
        accounts_by_device: Dict[str, list[Dict[str, Any]]] = {}
        for row in account_rows:
            accounts_by_device.setdefault(str(row["device_id"]), []).append(
                {
                    "id": row["id"],
                    "source": row["source"],
                    "label": row["label"],
                }
            )
        return {
            "devices": [
                {
                    "id": row["id"],
                    "name": row["name"],
                    "platform": row["platform"],
                    "enabled": bool(row["enabled"]),
                    "isLocal": bool(row["is_local"]),
                    "lastSeenAt": row["last_seen_at"],
                    "accounts": accounts_by_device.get(str(row["id"]), []),
                }
                for row in devices
            ]
        }
