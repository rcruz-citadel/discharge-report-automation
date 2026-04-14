"""Test fixtures and configuration.

Tests use AUTH_STUB_ENABLED=true to bypass Entra ID auth.
Database calls are mocked via override of the get_db dependency.
"""
import os

import pytest
from fastapi.testclient import TestClient

# Enable stub auth before importing app (env var must be set before Settings init)
os.environ["AUTH_STUB_ENABLED"] = "true"
os.environ["AUTH_STUB_EMAIL"] = "test@citadelhealth.com"
os.environ["AUTH_STUB_NAME"] = "Test User"
os.environ["AUTH_STUB_ROLE"] = "manager"
os.environ["DATABASE_URL"] = "postgresql+asyncpg://test:test@localhost:5432/test"

from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def client() -> TestClient:
    """Synchronous test client for FastAPI app."""
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c
