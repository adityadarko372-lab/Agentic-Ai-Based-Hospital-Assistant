"""Demo login and access control."""

from datetime import datetime, timedelta, timezone

import jwt

from app.core.config import get_settings
from app.db.seed import DEMO_PASSWORD
from tests.conftest import PATIENT_A, auth_headers


def test_login_with_demo_patient_returns_token_and_profile(client):
    response = client.post("/api/auth/login", json={"email": PATIENT_A, "password": DEMO_PASSWORD})

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["user"] == {"id": body["user"]["id"], "email": PATIENT_A, "full_name": "Asha Verma", "role": "patient"}
    # Password hashes must never leave the server.
    assert "password" not in response.text


def test_login_email_is_case_and_space_insensitive(client):
    response = client.post("/api/auth/login", json={"email": "  Patient@NovaHealth.DEMO ", "password": DEMO_PASSWORD})
    assert response.status_code == 200


def test_wrong_password_and_unknown_email_get_the_same_message(client):
    wrong_password = client.post("/api/auth/login", json={"email": PATIENT_A, "password": "not-the-password"})
    unknown_email = client.post("/api/auth/login", json={"email": "nobody@novahealth.demo", "password": DEMO_PASSWORD})

    assert wrong_password.status_code == unknown_email.status_code == 401
    assert wrong_password.json()["detail"] == unknown_email.json()["detail"] == "Incorrect email or password."


def test_login_validation_errors_are_friendly(client):
    response = client.post("/api/auth/login", json={"email": "", "password": ""})

    assert response.status_code == 422
    errors = response.json()["field_errors"]
    assert errors["email"] == "Please enter your email address."
    assert errors["password"] == "Please enter your password."


def test_overlong_password_is_rejected_without_error(client):
    response = client.post("/api/auth/login", json={"email": PATIENT_A, "password": "é" * 60})
    assert response.status_code == 401


def test_me_returns_the_signed_in_user(client):
    response = client.get("/api/auth/me", headers=auth_headers(client))

    assert response.status_code == 200
    assert response.json()["full_name"] == "Asha Verma"


def test_protected_endpoints_require_sign_in(client):
    for path in ("/api/auth/me", "/api/appointments/mine", "/api/activity/mine"):
        response = client.get(path)
        assert response.status_code == 401, path
        assert response.headers["www-authenticate"] == "Bearer"


def test_tampered_and_expired_tokens_are_rejected(client):
    secret = get_settings().session_secret
    expired = jwt.encode(
        {"sub": "1", "exp": datetime.now(timezone.utc) - timedelta(minutes=1)}, secret, algorithm="HS256"
    )
    forged = jwt.encode({"sub": "1", "exp": datetime.now(timezone.utc) + timedelta(hours=1)}, "a-different-secret-that-is-long-enough-0000", algorithm="HS256")
    unsigned = jwt.encode({"sub": "1", "exp": datetime.now(timezone.utc) + timedelta(hours=1)}, None, algorithm="none")

    for token in (expired, forged, unsigned, "garbage"):
        response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 401
