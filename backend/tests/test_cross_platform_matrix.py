from __future__ import annotations

import json
import ntpath
import sqlite3
import time
from pathlib import Path

import pytest

import app.config as config_module
import app.database as database_module
from app.agent import TokenAgent, agent_settings, load_config
from app.config import Settings
from app.database import Database
from app.ingest import IngestService
from app.schemas import IngestRequest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_EXAMPLES = PROJECT_ROOT / "docs" / "examples"


def _host_settings(root: Path) -> Settings:
    data_dir = root / "host-data"
    return Settings(
        data_dir=data_dir,
        database_path=data_dir / "dashboard.sqlite3",
        codex_home=root / "host-codex-disabled",
        hermes_database_path=root / "host-hermes-disabled" / "state.db",
        frontend_dist=root / "frontend-disabled",
        sync_interval_seconds=3600,
    )


def _write_codex_fixture(codex_home: Path, timestamp: float) -> None:
    path = codex_home / "sessions" / "collector-session.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    records = [
        {
            "timestamp": timestamp,
            "type": "session_meta",
            "payload": {"id": "raw-codex-session"},
        },
        {
            "timestamp": timestamp,
            "type": "turn_context",
            "payload": {"model": "gpt-cross-platform"},
        },
        {
            "timestamp": timestamp,
            "type": "event_msg",
            "payload": {
                "type": "token_count",
                "info": {
                    "total_token_usage": {
                        "input_tokens": 10,
                        "cached_input_tokens": 4,
                        "output_tokens": 2,
                        "reasoning_output_tokens": 1,
                    }
                },
            },
        },
    ]
    path.write_text(
        "".join(json.dumps(record) + "\n" for record in records),
        encoding="utf-8",
    )


def _write_hermes_fixture(path: Path, timestamp: float) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as conn:
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
        conn.execute(
            """
            INSERT INTO sessions (
                id, started_at, model, input_tokens, cache_read_tokens,
                cache_write_tokens, output_tokens, reasoning_tokens
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("raw-hermes-session", timestamp, "hermes-cross-platform", 5, 3, 0, 1, 0),
        )


@pytest.mark.parametrize(
    ("host_system", "expected_host_platform", "collector_platform"),
    [
        ("Darwin", "darwin", "macos"),
        ("Darwin", "darwin", "windows"),
        ("Windows", "windows", "macos"),
        ("Windows", "windows", "windows"),
    ],
    ids=("mac-host-mac-agent", "mac-host-win-agent", "win-host-mac-agent", "win-host-win-agent"),
)
def test_host_and_collector_platform_matrix(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    host_system: str,
    expected_host_platform: str,
    collector_platform: str,
) -> None:
    """The wire/database contract must not depend on either endpoint's OS."""

    monkeypatch.delenv("TOKEN_DASHBOARD_DEVICE_NAME", raising=False)
    monkeypatch.setattr(database_module.platform, "system", lambda: host_system)
    monkeypatch.setattr(database_module.platform, "node", lambda: f"{expected_host_platform}-host")

    host_settings = _host_settings(tmp_path)
    host_database = Database(host_settings.database_path)
    host_database.initialize()
    provisioned = host_database.provision_device(
        name=f"{collector_platform}-collector",
        platform_name=collector_platform,
        codex_label=f"Codex · {collector_platform}",
        hermes_label=f"Hermes · {collector_platform}",
    )

    collector_root = tmp_path / "collector"
    codex_home = collector_root / "codex"
    hermes_database = collector_root / "hermes" / "state.db"
    occurred_at = time.time() - 5
    _write_codex_fixture(codex_home, occurred_at)
    _write_hermes_fixture(hermes_database, occurred_at)

    config_path = collector_root / "agent-config.json"
    config_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "server_url": "https://replace-with-host.example.invalid",
                "device_id": provisioned["deviceId"],
                "device_name": provisioned["deviceName"],
                "device_token": provisioned["token"],
                "data_dir": str(collector_root / "data"),
                "codex_home": str(codex_home),
                "hermes_database_path": str(hermes_database),
                "account_labels": {
                    "codex": f"Codex · {collector_platform}",
                    "hermes": f"Hermes · {collector_platform}",
                },
                "timezone": "Asia/Shanghai",
                "sync_interval_seconds": 60,
            }
        ),
        encoding="utf-8",
    )

    # The collector has its own platform identity. The host row must retain the
    # platform captured above, proving that host and collector roles are separate.
    collector_system = "Darwin" if collector_platform == "macos" else "Windows"
    monkeypatch.setattr(database_module.platform, "system", lambda: collector_system)
    monkeypatch.setattr(database_module.platform, "node", lambda: f"{collector_platform}-collector")
    agent = TokenAgent(config_path)
    ingest = IngestService(host_database, host_settings)

    def deliver(body: dict) -> dict:
        payload = IngestRequest.model_validate(body)
        return ingest.ingest(provisioned["token"], payload)

    monkeypatch.setattr(agent, "_post", deliver)
    first = agent.sync_once()
    second = agent.sync_once()

    assert first["sync"]["status"] == "completed"
    assert first["upload"] == {"pending": 2, "uploaded": 2, "batches": 1}
    assert second["upload"] == {"pending": 0, "uploaded": 0, "batches": 0}

    with host_database.connect() as conn:
        local = conn.execute("SELECT * FROM devices WHERE id = 'local'").fetchone()
        remote = conn.execute(
            "SELECT * FROM devices WHERE id = ?", (provisioned["deviceId"],)
        ).fetchone()
        events = conn.execute(
            "SELECT * FROM usage_events WHERE device_id = ? ORDER BY source",
            (provisioned["deviceId"],),
        ).fetchall()
        accounts = conn.execute(
            "SELECT source, label FROM accounts WHERE device_id = ? ORDER BY source",
            (provisioned["deviceId"],),
        ).fetchall()

    assert local["platform"] == expected_host_platform
    assert remote["platform"] == collector_platform
    assert {row["source"] for row in events} == {"codex", "hermes"}
    assert sum(row["total_tokens"] for row in events) == 21
    assert all(len(row["external_session_id"]) == 64 for row in events)
    assert all("raw-" not in row["external_session_id"] for row in events)
    assert {row["label"] for row in accounts} == {
        f"Codex · {collector_platform}",
        f"Hermes · {collector_platform}",
    }


@pytest.mark.parametrize(
    ("filename", "platform_name"),
    [
        ("agent-config.macos.example.json", "macos"),
        ("agent-config.windows.example.json", "windows"),
    ],
)
def test_documented_agent_config_examples_are_safe_and_loadable(
    filename: str, platform_name: str
) -> None:
    path = CONFIG_EXAMPLES / filename
    raw = path.read_text(encoding="utf-8")
    config = load_config(path)

    assert config["schema_version"] == 1
    assert config["platform"] == platform_name
    assert config["server_url"] == "https://REPLACE_WITH_YOUR_HOST.example.invalid"
    assert config["device_id"] == "REPLACE_WITH_DEVICE_ID"
    assert config["device_token"] == "REPLACE_WITH_DEVICE_TOKEN"
    assert "100.64." not in raw
    assert ".ts.net" not in raw
    assert "/Users/" not in raw


def test_documented_macos_paths_expand_without_host_assumptions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    config = load_config(CONFIG_EXAMPLES / "agent-config.macos.example.json")
    settings = agent_settings(config)

    assert settings.data_dir == tmp_path / "Library" / "Application Support" / "Token Dashboard Agent"
    assert settings.codex_home == tmp_path / ".codex"
    assert settings.hermes_database_path == tmp_path / ".hermes" / "state.db"


def test_documented_windows_paths_follow_native_environment_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LOCALAPPDATA", r"C:\Users\Friend\AppData\Local")
    monkeypatch.setenv("USERPROFILE", r"C:\Users\Friend")
    config = load_config(CONFIG_EXAMPLES / "agent-config.windows.example.json")

    # ntpath models the expansion performed by os.path on Windows while this
    # test suite itself remains runnable on macOS/Linux CI.
    assert ntpath.expandvars(config["data_dir"]) == (
        r"C:\Users\Friend\AppData\Local\Token Dashboard Agent"
    )
    assert ntpath.expandvars(config["codex_home"]) == r"C:\Users\Friend\.codex"
    assert ntpath.expandvars(config["hermes_database_path"]) == (
        r"C:\Users\Friend\.hermes\state.db"
    )


def test_windows_embedded_runtime_has_default_timezone_fallback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def no_zoneinfo(_: str):
        raise config_module.ZoneInfoNotFoundError

    monkeypatch.setattr(config_module, "ZoneInfo", no_zoneinfo)
    settings = _host_settings(tmp_path)

    assert settings.timezone.utcoffset(None).total_seconds() == 8 * 60 * 60
