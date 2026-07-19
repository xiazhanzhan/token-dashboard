from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app


def test_api_partial_health_and_empty_ranges(settings):
    app = create_app(settings)
    with TestClient(app) as client:
        health = client.get("/api/health")
        assert health.status_code == 200
        assert health.json()["status"] in {"partial", "error"}

        response = client.get(
            "/api/timeseries",
            params={"granularity": "day", "from": "2024-02-28", "to": "2024-03-01"},
        )
        assert response.status_code == 200
        assert len(response.json()["points"]) == 6
        assert all(point["totalTokens"] == 0 for point in response.json()["points"])

        invalid = client.get(
            "/api/timeseries",
            params={"granularity": "day", "from": "2024-03-02", "to": "2024-03-01"},
        )
        assert invalid.status_code == 400

        root = client.get("/")
        assert root.status_code == 503
        assert "前端尚未构建" in root.json()["message"]
