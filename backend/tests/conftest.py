from __future__ import annotations

import os
import sqlite3
import tempfile
from pathlib import Path

import pytest

_IMPORT_DATA_DIR = Path(tempfile.mkdtemp(prefix="token-dashboard-import-"))
os.environ["TOKEN_DASHBOARD_DATA_DIR"] = str(_IMPORT_DATA_DIR)
os.environ["TOKEN_DASHBOARD_DB"] = str(_IMPORT_DATA_DIR / "import.sqlite3")

from app.config import Settings  # noqa: E402
from app.database import Database  # noqa: E402


def create_hermes_database(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute(
        """
        CREATE TABLE sessions (
            id TEXT PRIMARY KEY,
            started_at REAL NOT NULL,
            model TEXT,
            input_tokens INTEGER DEFAULT 0,
            cache_read_tokens INTEGER DEFAULT 0,
            cache_write_tokens INTEGER DEFAULT 0,
            output_tokens INTEGER DEFAULT 0,
            reasoning_tokens INTEGER DEFAULT 0
        )
        """
    )
    conn.commit()
    conn.close()


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    codex = tmp_path / ".codex"
    (codex / "sessions").mkdir(parents=True)
    hermes = tmp_path / ".hermes" / "state.db"
    create_hermes_database(hermes)
    data_dir = tmp_path / "data"
    return Settings(
        data_dir=data_dir,
        database_path=data_dir / "dashboard.sqlite3",
        codex_home=codex,
        hermes_database_path=hermes,
        frontend_dist=tmp_path / "missing-dist",
        sync_interval_seconds=3600,
    )


@pytest.fixture
def database(settings: Settings) -> Database:
    db = Database(settings.database_path)
    db.initialize()
    return db
