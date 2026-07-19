from __future__ import annotations

import time

from fastapi.testclient import TestClient

from app.main import create_app


def test_remote_ingest_auth_dedup_and_device_filters(database, settings):
    provisioned = database.provision_device(
        name="Test Windows PC",
        platform_name="windows",
        codex_label="Codex · MSI",
        hermes_label="Hermes · MSI",
    )
    payload = {
        "schemaVersion": 1,
        "batchId": "batch-windows-001",
        "events": [
            {
                "schemaVersion": 1,
                "eventId": "windows-event-001",
                "source": "codex",
                "sessionHash": "session-hash-001",
                "occurredAt": time.time(),
                "model": "gpt-windows",
                "inputTokens": 10,
                "cacheReadTokens": 20,
                "cacheWriteTokens": 0,
                "outputTokens": 5,
                "reasoningTokens": 2,
                "totalTokens": 999,
            }
        ],
    }
    app = create_app(settings)
    with TestClient(app) as client:
        denied = client.post("/api/v1/ingest/events", json=payload)
        assert denied.status_code == 401

        headers = {"Authorization": f"Bearer {provisioned['token']}"}
        first = client.post("/api/v1/ingest/events", json=payload, headers=headers)
        assert first.status_code == 200
        assert first.json()["inserted"] == 1

        repeated = client.post("/api/v1/ingest/events", json=payload, headers=headers)
        assert repeated.status_code == 200
        assert repeated.json()["status"] == "duplicate_batch"

        device_id = provisioned["deviceId"]
        summary = client.get("/api/summary", params={"device": device_id}).json()
        assert summary["periods"]["today"]["current"]["totalTokens"] == 35

        account_id = f"{device_id}:codex"
        account_summary = client.get(
            "/api/summary", params={"account": account_id}
        ).json()
        assert account_summary["periods"]["today"]["current"]["totalTokens"] == 35

        sessions = client.get(
            "/api/sessions", params={"device": device_id}
        ).json()["sessions"]
        assert sessions[0]["deviceName"] == "Test Windows PC"
        assert sessions[0]["accountLabel"] == "Codex · MSI"

        devices = client.get("/api/devices").json()["devices"]
        remote = next(item for item in devices if item["id"] == device_id)
        assert remote["platform"] == "windows"
        assert remote["lastSeenAt"] is not None

        wsl_payload = {
            "schemaVersion": 1,
            "batchId": "batch-wsl-hermes-001",
            "events": [
                {
                    "schemaVersion": 1,
                    "eventId": "wsl-hermes-event-001",
                    "source": "hermes",
                    "accountKey": "hermes-wsl-ubuntu",
                    "accountLabel": "Hermes CLI · WSL Ubuntu",
                    "sessionHash": "wsl-session-hash-001",
                    "occurredAt": time.time(),
                    "model": "hermes-model",
                    "inputTokens": 7,
                    "outputTokens": 3,
                    "totalTokens": 10,
                }
            ],
        }
        wsl = client.post(
            "/api/v1/ingest/events", json=wsl_payload, headers=headers
        )
        assert wsl.status_code == 200
        wsl_account = f"{device_id}:hermes-wsl-ubuntu"
        wsl_summary = client.get(
            "/api/summary", params={"account": wsl_account}
        ).json()
        assert wsl_summary["periods"]["today"]["current"]["totalTokens"] == 10
        refreshed = client.get("/api/devices").json()["devices"]
        remote = next(item for item in refreshed if item["id"] == device_id)
        labels = {item["id"]: item["label"] for item in remote["accounts"]}
        assert labels[wsl_account] == "Hermes CLI · WSL Ubuntu"

    with database.connect() as conn:
        row = conn.execute(
            "SELECT * FROM usage_events WHERE device_id = ?", (provisioned["deviceId"],)
        ).fetchone()
    assert row["total_tokens"] == 35
    assert row["reasoning_tokens"] == 2
