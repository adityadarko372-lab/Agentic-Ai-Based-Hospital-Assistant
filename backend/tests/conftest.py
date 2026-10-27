"""Shared pytest setup.

Environment variables take precedence over the developer's `.env` file, so
pinning them here keeps tests deterministic even if optional features are
switched on locally. Every test that uses the `client` fixture gets its own
empty SQLite file, so tests never touch the real demo database.
"""

import os
import tempfile
from collections.abc import Iterator
from datetime import timedelta
from pathlib import Path

import pytest

os.environ.update(
    {
        "ENVIRONMENT": "test",
        "INTENT_CLASSIFIER": "rules",
        "HEALTH_INFO_ENABLED": "false",
        "LLM_PHRASING_ENABLED": "false",
        "FRONT_DESK_ENABLED": "false",
        "CORS_ORIGINS": "http://127.0.0.1:5173,http://localhost:5173",
        "SESSION_SECRET": "test-secret-not-for-production-0123456789abcdef",
        "BCRYPT_ROUNDS": "4",  # fast hashing for tests only
        # Default database for modules imported at collection time.
        "DATABASE_PATH": str(Path(tempfile.mkdtemp(prefix="nova_health_tests_")) / "import.db"),
    }
)

from fastapi.testclient import TestClient  # noqa: E402

from app.core.clock import today_in_india  # noqa: E402
from app.core.config import get_settings  # noqa: E402
from app.db.seed import DEMO_PASSWORD  # noqa: E402
from app.db.session import reset_engine  # noqa: E402

PATIENT_A = "patient@novahealth.demo"
PATIENT_B = "rohan.mehta@novahealth.demo"


def build_client(database_path: Path) -> TestClient:
    """A TestClient for a fresh app instance bound to `database_path`."""
    os.environ["DATABASE_PATH"] = str(database_path)
    get_settings.cache_clear()
    reset_engine()
    from app.main import create_app

    return TestClient(create_app())


@pytest.fixture
def database_path(tmp_path: Path) -> Path:
    return tmp_path / "nova_health_test.db"


@pytest.fixture
def client(database_path: Path) -> Iterator[TestClient]:
    # The context manager runs the app's start-up (create tables + seed data).
    with build_client(database_path) as test_client:
        yield test_client
    reset_engine()


def auth_headers(client: TestClient, email: str = PATIENT_A) -> dict[str, str]:
    response = client.post("/api/auth/login", json={"email": email, "password": DEMO_PASSWORD})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def valid_appointment(**overrides) -> dict:
    payload = {
        "patient_name": "Asha Verma",
        "department_id": "cardiology",
        "preferred_date": (today_in_india() + timedelta(days=7)).isoformat(),
        "reason": "Follow-up consultation for occasional palpitations.",
    }
    payload.update(overrides)
    return payload
