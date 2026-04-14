"""Tests for health and auth stub endpoints."""
from fastapi.testclient import TestClient


def test_health(client: TestClient) -> None:
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["version"] == "3.0.0"


def test_me_stub(client: TestClient) -> None:
    """In stub mode, GET /api/auth/me returns the stub user without a cookie."""
    resp = client.get("/api/auth/me")
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == "test@citadelhealth.com"
    assert data["name"] == "Test User"
    assert data["role"] == "manager"


def test_me_requires_auth_without_stub() -> None:
    """Without stub mode, GET /api/auth/me returns 401 when no cookie is present."""
    import os

    # Temporarily disable stub
    os.environ["AUTH_STUB_ENABLED"] = "false"
    # Re-import to pick up new env value — requires cache invalidation
    from functools import lru_cache

    from app.config import get_settings
    get_settings.cache_clear()

    from fastapi.testclient import TestClient
    from app.main import app as _app

    with TestClient(_app, raise_server_exceptions=False) as c:
        resp = c.get("/api/auth/me")
        assert resp.status_code == 401

    # Restore stub mode
    os.environ["AUTH_STUB_ENABLED"] = "true"
    get_settings.cache_clear()
