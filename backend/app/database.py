from __future__ import annotations

import json
import os
import platform
import secrets
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Iterator, Optional


SCHEMA = """
CREATE TABLE IF NOT EXISTS usage_events (
    id TEXT PRIMARY KEY,
    source TEXT NOT NULL CHECK (source IN ('codex', 'hermes')),
    source_key TEXT NOT NULL,
    external_session_id TEXT NOT NULL,
    occurred_at REAL NOT NULL,
    local_day TEXT NOT NULL,
    model TEXT NOT NULL DEFAULT 'unknown',
    input_tokens INTEGER NOT NULL DEFAULT 0 CHECK (input_tokens >= 0),
    cache_read_tokens INTEGER NOT NULL DEFAULT 0 CHECK (cache_read_tokens >= 0),
    cache_write_tokens INTEGER NOT NULL DEFAULT 0 CHECK (cache_write_tokens >= 0),
    output_tokens INTEGER NOT NULL DEFAULT 0 CHECK (output_tokens >= 0),
    reasoning_tokens INTEGER NOT NULL DEFAULT 0 CHECK (reasoning_tokens >= 0),
    total_tokens INTEGER NOT NULL DEFAULT 0 CHECK (total_tokens >= 0),
    metadata_json TEXT NOT NULL DEFAULT '{}',
    device_id TEXT NOT NULL DEFAULT 'local',
    account_id TEXT NOT NULL DEFAULT 'local',
    created_at REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_usage_events_day
    ON usage_events(local_day, source, model);
CREATE INDEX IF NOT EXISTS idx_usage_events_session
    ON usage_events(source, external_session_id);
CREATE INDEX IF NOT EXISTS idx_usage_events_occurred
    ON usage_events(occurred_at DESC);

CREATE TABLE IF NOT EXISTS source_cursors (
    source TEXT NOT NULL,
    source_key TEXT NOT NULL,
    inode INTEGER,
    byte_offset INTEGER NOT NULL DEFAULT 0,
    file_size INTEGER NOT NULL DEFAULT 0,
    file_mtime REAL NOT NULL DEFAULT 0,
    state_json TEXT NOT NULL DEFAULT '{}',
    updated_at REAL NOT NULL,
    PRIMARY KEY (source, source_key)
);

CREATE TABLE IF NOT EXISTS hermes_sessions (
    session_id TEXT PRIMARY KEY,
    generation INTEGER NOT NULL DEFAULT 0,
    started_at REAL NOT NULL,
    model TEXT NOT NULL,
    input_tokens INTEGER NOT NULL DEFAULT 0,
    cache_read_tokens INTEGER NOT NULL DEFAULT 0,
    cache_write_tokens INTEGER NOT NULL DEFAULT 0,
    output_tokens INTEGER NOT NULL DEFAULT 0,
    reasoning_tokens INTEGER NOT NULL DEFAULT 0,
    last_seen_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS daily_snapshots (
    snapshot_day TEXT NOT NULL,
    source TEXT NOT NULL,
    model TEXT NOT NULL,
    input_tokens INTEGER NOT NULL DEFAULT 0,
    cache_read_tokens INTEGER NOT NULL DEFAULT 0,
    cache_write_tokens INTEGER NOT NULL DEFAULT 0,
    output_tokens INTEGER NOT NULL DEFAULT 0,
    reasoning_tokens INTEGER NOT NULL DEFAULT 0,
    total_tokens INTEGER NOT NULL DEFAULT 0,
    event_count INTEGER NOT NULL DEFAULT 0,
    captured_at REAL NOT NULL,
    PRIMARY KEY (snapshot_day, source, model)
);

CREATE TABLE IF NOT EXISTS source_status (
    source TEXT PRIMARY KEY,
    available INTEGER NOT NULL DEFAULT 0,
    last_success_at REAL,
    last_error TEXT,
    records_seen INTEGER NOT NULL DEFAULT 0,
    updated_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS sync_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at REAL NOT NULL,
    completed_at REAL,
    status TEXT NOT NULL,
    codex_events_added INTEGER NOT NULL DEFAULT 0,
    hermes_events_added INTEGER NOT NULL DEFAULT 0,
    error TEXT
);

CREATE TABLE IF NOT EXISTS devices (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    platform TEXT NOT NULL DEFAULT 'unknown',
    token_hash TEXT UNIQUE,
    enabled INTEGER NOT NULL DEFAULT 1,
    is_local INTEGER NOT NULL DEFAULT 0,
    last_seen_at REAL,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS accounts (
    id TEXT PRIMARY KEY,
    device_id TEXT NOT NULL,
    source TEXT NOT NULL CHECK (source IN ('codex', 'hermes')),
    label TEXT NOT NULL,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    FOREIGN KEY(device_id) REFERENCES devices(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS ingest_batches (
    device_id TEXT NOT NULL,
    batch_id TEXT NOT NULL,
    received_at REAL NOT NULL,
    event_count INTEGER NOT NULL DEFAULT 0,
    inserted_count INTEGER NOT NULL DEFAULT 0,
    duplicate_count INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY(device_id, batch_id),
    FOREIGN KEY(device_id) REFERENCES devices(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS agent_delivery (
    destination_id TEXT NOT NULL,
    event_id TEXT NOT NULL,
    uploaded_at REAL NOT NULL,
    batch_id TEXT NOT NULL,
    PRIMARY KEY(destination_id, event_id)
);
"""


class Database:
    def __init__(self, path: Path):
        self.path = Path(path)

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as conn:
            conn.executescript(SCHEMA)
            self._migrate(conn)
            conn.commit()

    @staticmethod
    def _migrate(conn: sqlite3.Connection) -> None:
        """Apply additive migrations without invalidating an existing local database."""
        columns = {
            row["name"] for row in conn.execute("PRAGMA table_info(usage_events)")
        }
        if "device_id" not in columns:
            conn.execute(
                "ALTER TABLE usage_events ADD COLUMN device_id TEXT NOT NULL DEFAULT 'local'"
            )
        if "account_id" not in columns:
            conn.execute(
                "ALTER TABLE usage_events ADD COLUMN account_id TEXT NOT NULL DEFAULT 'local'"
            )

        hermes_columns = {
            row["name"] for row in conn.execute("PRAGMA table_info(hermes_sessions)")
        }
        if "generation" not in hermes_columns:
            conn.execute(
                "ALTER TABLE hermes_sessions ADD COLUMN generation INTEGER NOT NULL DEFAULT 0"
            )

        # CREATE TABLE statements above are harmless on existing databases and
        # make the migration work for databases created by older releases.
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS devices (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                platform TEXT NOT NULL DEFAULT 'unknown',
                token_hash TEXT UNIQUE,
                enabled INTEGER NOT NULL DEFAULT 1,
                is_local INTEGER NOT NULL DEFAULT 0,
                last_seen_at REAL,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS accounts (
                id TEXT PRIMARY KEY,
                device_id TEXT NOT NULL,
                source TEXT NOT NULL CHECK (source IN ('codex', 'hermes')),
                label TEXT NOT NULL,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL,
                FOREIGN KEY(device_id) REFERENCES devices(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS ingest_batches (
                device_id TEXT NOT NULL,
                batch_id TEXT NOT NULL,
                received_at REAL NOT NULL,
                event_count INTEGER NOT NULL DEFAULT 0,
                inserted_count INTEGER NOT NULL DEFAULT 0,
                duplicate_count INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY(device_id, batch_id),
                FOREIGN KEY(device_id) REFERENCES devices(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_usage_events_device
                ON usage_events(device_id, account_id, local_day);
            CREATE INDEX IF NOT EXISTS idx_accounts_device
                ON accounts(device_id, source);
            """
        )
        delivery_columns = {
            row["name"] for row in conn.execute("PRAGMA table_info(agent_delivery)")
        }
        if "destination_id" not in delivery_columns:
            conn.executescript(
                """
                ALTER TABLE agent_delivery RENAME TO agent_delivery_legacy;
                CREATE TABLE agent_delivery (
                    destination_id TEXT NOT NULL,
                    event_id TEXT NOT NULL,
                    uploaded_at REAL NOT NULL,
                    batch_id TEXT NOT NULL,
                    PRIMARY KEY(destination_id, event_id)
                );
                INSERT INTO agent_delivery (
                    destination_id, event_id, uploaded_at, batch_id
                )
                SELECT 'legacy', event_id, uploaded_at, batch_id
                FROM agent_delivery_legacy;
                DROP TABLE agent_delivery_legacy;
                """
            )
        account_schema = conn.execute(
            "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'accounts'"
        ).fetchone()
        if account_schema and "UNIQUE(device_id, source)" in (account_schema["sql"] or ""):
            conn.executescript(
                """
                DROP INDEX IF EXISTS idx_accounts_device;
                ALTER TABLE accounts RENAME TO accounts_single_source;
                CREATE TABLE accounts (
                    id TEXT PRIMARY KEY,
                    device_id TEXT NOT NULL,
                    source TEXT NOT NULL CHECK (source IN ('codex', 'hermes')),
                    label TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL,
                    FOREIGN KEY(device_id) REFERENCES devices(id) ON DELETE CASCADE
                );
                INSERT INTO accounts (
                    id, device_id, source, label, created_at, updated_at
                )
                SELECT id, device_id, source, label, created_at, updated_at
                FROM accounts_single_source;
                DROP TABLE accounts_single_source;
                CREATE INDEX idx_accounts_device ON accounts(device_id, source);
                """
            )
        now = time.time()
        configured_local_name = os.environ.get("TOKEN_DASHBOARD_DEVICE_NAME", "").strip()
        local_name = configured_local_name or platform.node() or "Mac mini"
        conn.execute(
            """
            INSERT INTO devices (
                id, name, platform, enabled, is_local, last_seen_at,
                created_at, updated_at
            ) VALUES ('local', ?, ?, 1, 1, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                name = CASE WHEN ? <> '' THEN excluded.name ELSE devices.name END,
                platform = excluded.platform,
                is_local = 1,
                updated_at = excluded.updated_at
            """,
            (
                local_name,
                platform.system().lower() or "unknown",
                now,
                now,
                now,
                configured_local_name,
            ),
        )
        for source, label in (("codex", "Codex · 本机"), ("hermes", "Hermes · 本机")):
            account_id = f"local:{source}"
            conn.execute(
                """
                INSERT INTO accounts (
                    id, device_id, source, label, created_at, updated_at
                ) VALUES (?, 'local', ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET updated_at = excluded.updated_at
                """,
                (account_id, source, label, now, now),
            )
            conn.execute(
                """
                UPDATE usage_events
                SET device_id = 'local', account_id = ?
                WHERE device_id = 'local'
                  AND source = ?
                  AND (account_id = 'local' OR account_id = '')
                """,
                (account_id, source),
            )

    def connect(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        try:
            self.path.parent.chmod(0o700)
        except OSError:
            # Windows ACLs are managed separately by the agent installer.
            pass
        conn = sqlite3.connect(str(self.path), timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA busy_timeout=10000")
        for private_file in (
            self.path,
            Path(f"{self.path}-wal"),
            Path(f"{self.path}-shm"),
        ):
            if private_file.exists():
                try:
                    private_file.chmod(0o600)
                except OSError:
                    pass
        return conn

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        conn = self.connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    @staticmethod
    def get_cursor(
        conn: sqlite3.Connection, source: str, source_key: str
    ) -> Optional[Dict[str, Any]]:
        row = conn.execute(
            "SELECT * FROM source_cursors WHERE source = ? AND source_key = ?",
            (source, source_key),
        ).fetchone()
        if row is None:
            return None
        result = dict(row)
        try:
            result["state"] = json.loads(result.pop("state_json"))
        except (TypeError, json.JSONDecodeError):
            result["state"] = {}
        return result

    @staticmethod
    def save_cursor(
        conn: sqlite3.Connection,
        *,
        source: str,
        source_key: str,
        inode: int,
        byte_offset: int,
        file_size: int,
        file_mtime: float,
        state: Dict[str, Any],
    ) -> None:
        conn.execute(
            """
            INSERT INTO source_cursors (
                source, source_key, inode, byte_offset, file_size,
                file_mtime, state_json, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(source, source_key) DO UPDATE SET
                inode = excluded.inode,
                byte_offset = excluded.byte_offset,
                file_size = excluded.file_size,
                file_mtime = excluded.file_mtime,
                state_json = excluded.state_json,
                updated_at = excluded.updated_at
            """,
            (
                source,
                source_key,
                inode,
                byte_offset,
                file_size,
                file_mtime,
                json.dumps(state, separators=(",", ":"), sort_keys=True),
                time.time(),
            ),
        )

    @staticmethod
    def insert_event(conn: sqlite3.Connection, event: Dict[str, Any]) -> bool:
        event = dict(event)
        event.setdefault("device_id", "local")
        event.setdefault("account_id", f"local:{event.get('source', 'unknown')}")
        cursor = conn.execute(
            """
            INSERT OR IGNORE INTO usage_events (
                id, source, source_key, external_session_id, occurred_at,
                local_day, model, input_tokens, cache_read_tokens,
                cache_write_tokens, output_tokens, reasoning_tokens,
                total_tokens, metadata_json, device_id, account_id, created_at
            ) VALUES (
                :id, :source, :source_key, :external_session_id, :occurred_at,
                :local_day, :model, :input_tokens, :cache_read_tokens,
                :cache_write_tokens, :output_tokens, :reasoning_tokens,
                :total_tokens, :metadata_json, :device_id, :account_id, :created_at
            )
            """,
            event,
        )
        return cursor.rowcount == 1

    def provision_device(
        self,
        *,
        name: str,
        platform_name: str = "windows",
        codex_label: str = "Codex · Windows",
        hermes_label: str = "Hermes · Windows",
    ) -> Dict[str, str]:
        import hashlib

        normalized_name = name.strip()
        if not normalized_name:
            raise ValueError("设备名称不能为空")
        device_id = "dev_" + secrets.token_hex(8)
        token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        now = time.time()
        with self.transaction() as conn:
            conn.execute(
                """
                INSERT INTO devices (
                    id, name, platform, token_hash, enabled, is_local,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, 1, 0, ?, ?)
                """,
                (device_id, normalized_name, platform_name, token_hash, now, now),
            )
            for source, label in (("codex", codex_label), ("hermes", hermes_label)):
                conn.execute(
                    """
                    INSERT INTO accounts (
                        id, device_id, source, label, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (f"{device_id}:{source}", device_id, source, label, now, now),
                )
        return {"deviceId": device_id, "deviceName": normalized_name, "token": token}

    @staticmethod
    def set_source_status(
        conn: sqlite3.Connection,
        source: str,
        *,
        available: bool,
        records_seen: int = 0,
        error: Optional[str] = None,
    ) -> None:
        now = time.time()
        conn.execute(
            """
            INSERT INTO source_status (
                source, available, last_success_at, last_error,
                records_seen, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(source) DO UPDATE SET
                available = excluded.available,
                last_success_at = CASE
                    WHEN excluded.available = 1 THEN excluded.last_success_at
                    ELSE source_status.last_success_at
                END,
                last_error = excluded.last_error,
                records_seen = excluded.records_seen,
                updated_at = excluded.updated_at
            """,
            (
                source,
                int(available),
                now if available else None,
                error,
                records_seen,
                now,
            ),
        )
