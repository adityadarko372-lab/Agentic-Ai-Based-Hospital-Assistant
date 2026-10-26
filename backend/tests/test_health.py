"""Smoke tests for the health endpoint and CORS policy."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_returns_ok_and_service_identity():
    response = client.get("/api/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "Nova Health"
    assert body["demo_data"] is True
    assert "server_time" in body


def test_health_reports_optional_features_off_by_default():
    features = client.get("/api/health").json()["features"]

    # The required demo must not depend on any optional AI component.
    assert features["intent_classifier"] == "rules"
    assert features["health_info_enabled"] is False
    assert features["llm_phrasing_enabled"] is False
    assert features["front_desk_enabled"] is False


def test_cors_allows_local_frontend_origin():
    response = client.get("/api/health", headers={"Origin": "http://127.0.0.1:5173"})

    assert response.headers.get("access-control-allow-origin") == "http://127.0.0.1:5173"


def test_cors_rejects_unknown_origin():
    response = client.get("/api/health", headers={"Origin": "http://evil.example"})

    assert "access-control-allow-origin" not in response.headers


def test_unknown_route_returns_404():
    assert client.get("/api/does-not-exist").status_code == 404
