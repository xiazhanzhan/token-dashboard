from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path

import pytest

from app.agent import TokenAgent, load_config
from app.collectors.codex import CodexCollector
from app.collectors.common import make_event
from app.config import Settings
from app.database import Database
from app.ingest import IngestService
from app.schemas import IngestRequest


def _token_record(total_input: int, output: int) -> dict:
    return {
        "timestamp": "2026-07-19T01:02:03Z",
        "type": "event_msg",
        "payload": {
            "type": "token_count",
            "info": {
                "total_token_usage": {
                    "input_tokens": total_input,
                    "cached_input_tokens": 0,
                    "output_tokens": output,
                    "reasoning_output_tokens": 0,
                }
            },
        },
    }


def test_local_codex_rebuild_never_deletes_remote_events(database, settings):
    remote = database.provision_device(name="Remote Mac", platform_name="macos")
    remote_id = remote["deviceId"]
    event = make_event(
        event_id="remote-event-kept",
        source="codex",
        source_key=f"remote:{remote_id}",
        session_id="remote-session-hash",
        occurred_at=time.time(),
        tz=settings.timezone,
        model="remote-model",
        input_tokens=10,
        cache_read_tokens=0,
        cache_write_tokens=0,
        output_tokens=2,
        reasoning_tokens=0,
        metadata={"remote": True},
    )
    event["device_id"] = remote_id
    event["account_id"] = f"{remote_id}:codex"
    with database.transaction() as conn:
        database.insert_event(conn, event)

    path = settings.codex_home / "sessions" / "active.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"type": "session_meta", "payload": {"id": "local"}})
        + "\n"
        + json.dumps(_token_record(500, 50))
        + "\n",
        encoding="utf-8",
    )
    collector = CodexCollector(database, settings.codex_home, settings.timezone)
    with database.transaction() as conn:
        collector.collect(conn)

    # Truncate the active file so the local cursor must rebuild.
    path.write_text(json.dumps(_token_record(1, 1)) + "\n", encoding="utf-8")
    with database.transaction() as conn:
        result = collector.collect(conn)
    assert result["rebuilds"] == 1
    with database.connect() as conn:
        kept = conn.execute(
            "SELECT total_tokens FROM usage_events WHERE id = 'remote-event-kept'"
        ).fetchone()
    assert kept is not None
    assert kept["total_tokens"] == 12


def _create_hermes(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as conn:
        conn.execute(
            """
            CREATE TABLE sessions (
                id TEXT PRIMARY KEY, started_at REAL NOT NULL, model TEXT,
                input_tokens INTEGER, cache_read_tokens INTEGER,
                cache_write_tokens INTEGER, output_tokens INTEGER,
                reasoning_tokens INTEGER
            )
            """
        )
        conn.execute(
            """
            INSERT INTO sessions VALUES ('session-reset', ?, 'hermes-model',
                                         100, 50, 0, 20, 5)
            """,
            (time.time() - 60,),
        )


def test_hermes_reset_replaces_remote_session_authoritatively(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    host_data = tmp_path / "host"
    host_settings = Settings(
        data_dir=host_data,
        database_path=host_data / "host.sqlite3",
        codex_home=tmp_path / "disabled-host-codex",
        hermes_database_path=tmp_path / "disabled-host-hermes.db",
        frontend_dist=tmp_path / "missing-frontend",
        collect_local=False,
    )
    host = Database(host_settings.database_path)
    host.initialize()
    provisioned = host.provision_device(name="Reset Agent", platform_name="macos")

    agent_root = tmp_path / "agent"
    hermes_path = agent_root / "hermes" / "state.db"
    _create_hermes(hermes_path)
    config_path = agent_root / "agent-config.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "server_url": "https://host.example.invalid",
                "device_id": provisioned["deviceId"],
                "device_name": provisioned["deviceName"],
                "device_token": provisioned["token"],
                "data_dir": str(agent_root / "data"),
                "codex_home": str(agent_root / "missing-codex"),
                "hermes_database_path": str(hermes_path),
            }
        ),
        encoding="utf-8",
    )
    agent = TokenAgent(config_path)
    ingest = IngestService(host, host_settings)

    def deliver(body: dict) -> dict:
        return ingest.ingest(
            provisioned["token"], IngestRequest.model_validate(body)
        )

    monkeypatch.setattr(agent, "_post", deliver)
    first = agent.sync_once()
    assert first["upload"]["uploaded"] == 1

    with sqlite3.connect(hermes_path) as source:
        source.execute(
            """
            UPDATE sessions SET input_tokens=150, cache_read_tokens=70,
                                output_tokens=30, reasoning_tokens=8
            WHERE id='session-reset'
            """
        )
    agent.sync_once()
    with host.connect() as conn:
        assert conn.execute(
            "SELECT SUM(total_tokens) FROM usage_events WHERE device_id = ?",
            (provisioned["deviceId"],),
        ).fetchone()[0] == 250

    with sqlite3.connect(hermes_path) as source:
        source.execute(
            """
            UPDATE sessions SET input_tokens=10, cache_read_tokens=2,
                                output_tokens=5, reasoning_tokens=2
            WHERE id='session-reset'
            """
        )
    reset = agent.sync_once()
    assert reset["upload"]["uploaded"] == 1
    with host.connect() as conn:
        rows = conn.execute(
            "SELECT * FROM usage_events WHERE device_id = ?",
            (provisioned["deviceId"],),
        ).fetchall()
    assert len(rows) == 1
    assert rows[0]["total_tokens"] == 17


def test_remote_http_configuration_is_rejected(tmp_path: Path):
    path = tmp_path / "agent-config.json"
    path.write_text(
        json.dumps(
            {
                "server_url": "http://192.168.1.20:8765",
                "device_id": "dev_example",
                "device_token": "secret-example",
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(RuntimeError, match="HTTPS"):
        load_config(path)
