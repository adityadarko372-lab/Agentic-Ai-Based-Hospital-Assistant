"""Phase 5: front-desk review (human-in-the-loop) and the new demo accounts."""

import pytest

from app.core.config import get_settings
from app.db.seed import DEMO_PASSWORD
from app.db.session import reset_engine
from tests.conftest import auth_headers, build_client, valid_appointment

STAFF = "frontdesk@novahealth.demo"


@pytest.fixture
def desk_client(database_path, monkeypatch):
    monkeypatch.setenv("FRONT_DESK_ENABLED", "true")
    with build_client(database_path) as client:
        yield client
    reset_engine()
    monkeypatch.undo()
    get_settings.cache_clear()  # later tests must see the default (off) again


def submit(client, email="patient@novahealth.demo", key="desk-key-000001", **overrides):
    headers = {**auth_headers(client, email), "Idempotency-Key": key}
    response = client.post("/api/appointments", json=valid_appointment(**overrides), headers=headers)
    assert response.status_code == 201, response.text
    return response.json()["reference"]


@pytest.mark.parametrize(
    ("email", "name"),
    [
        ("aditya.singh@novahealth.demo", "Aditya Singh"),
        ("aaryan.naik@novahealth.demo", "Aaryan Naik"),
        ("bhavish.keni@novahealth.demo", "Bhavish Keni"),
    ],
)
def test_new_demo_patients_can_sign_in(client, email, name):
    body = client.post("/api/auth/login", json={"email": email, "password": DEMO_PASSWORD}).json()
    assert body["user"]["full_name"] == name
    assert body["user"]["role"] == "patient"


def test_front_desk_account_has_the_staff_role_and_no_patient_access(client):
    headers = auth_headers(client, STAFF)
    assert client.get("/api/auth/me", headers=headers).json()["role"] == "front_desk"
    assert client.get("/api/appointments/mine", headers=headers).status_code == 403
    assert client.post("/api/assistant/message", json={"message": "hi"}, headers=headers).status_code == 403


def test_front_desk_is_off_by_default(client):
    assert client.get("/api/front-desk/requests", headers=auth_headers(client, STAFF)).status_code == 404


def test_patients_cannot_use_the_front_desk(desk_client):
    reference = submit(desk_client)
    patient = auth_headers(desk_client)
    assert desk_client.get("/api/front-desk/requests", headers=patient).status_code == 403
    response = desk_client.post(f"/api/front-desk/requests/{reference}/decision", json={"decision": "confirm"}, headers=patient)
    assert response.status_code == 403
    assert desk_client.get("/api/front-desk/requests").status_code == 401


def test_staff_sees_pending_requests_from_all_patients(desk_client):
    first = submit(desk_client)
    second = submit(desk_client, "aditya.singh@novahealth.demo", "desk-key-000002", patient_name="Aditya Singh")

    listed = desk_client.get("/api/front-desk/requests", headers=auth_headers(desk_client, STAFF)).json()
    assert {item["reference"] for item in listed} == {first, second}
    assert {item["patient_email"] for item in listed} == {"patient@novahealth.demo", "aditya.singh@novahealth.demo"}


def test_confirm_updates_the_patient_view_and_history(desk_client):
    reference = submit(desk_client)
    staff = auth_headers(desk_client, STAFF)

    decided = desk_client.post(
        f"/api/front-desk/requests/{reference}/decision", json={"decision": "confirm", "note": "Please arrive 15 minutes early."}, headers=staff
    )
    assert decided.status_code == 200
    assert decided.json()["status"] == "confirmed"
    assert decided.json()["reviewed_by"] == "Meera Desai"

    patient = auth_headers(desk_client)
    mine = desk_client.get("/api/appointments/mine", headers=patient).json()[0]
    assert mine["status"] == "confirmed"
    assert mine["review_note"] == "Please arrive 15 minutes early."
    assert mine["reviewed_at"]
    event = desk_client.get("/api/activity/mine", headers=patient).json()[0]
    assert event["event_type"] == "appointment.confirmed"
    assert event["actor"] == "Front Desk"
    # No longer in the pending queue.
    assert desk_client.get("/api/front-desk/requests", headers=staff).json() == []
    confirmed = desk_client.get("/api/front-desk/requests?status=confirmed", headers=staff).json()
    assert [item["reference"] for item in confirmed] == [reference]
    everything = desk_client.get("/api/front-desk/requests?status=all", headers=staff).json()
    assert [item["reference"] for item in everything] == [reference]
    assert desk_client.get("/api/front-desk/requests?status=bogus", headers=staff).status_code == 422


def test_a_request_can_only_be_decided_once(desk_client):
    reference = submit(desk_client)
    staff = auth_headers(desk_client, STAFF)
    url = f"/api/front-desk/requests/{reference}/decision"

    assert desk_client.post(url, json={"decision": "confirm"}, headers=staff).status_code == 200
    again = desk_client.post(url, json={"decision": "decline", "note": "Changed my mind"}, headers=staff)
    assert again.status_code == 409
    assert desk_client.get("/api/appointments/mine", headers=auth_headers(desk_client)).json()[0]["status"] == "confirmed"


def test_decline_needs_a_note_and_cancelled_requests_cannot_be_decided(desk_client):
    reference = submit(desk_client)
    staff = auth_headers(desk_client, STAFF)
    url = f"/api/front-desk/requests/{reference}/decision"

    missing_note = desk_client.post(url, json={"decision": "decline"}, headers=staff)
    assert missing_note.status_code == 422
    assert "note" in missing_note.json()["field_errors"]

    desk_client.post(f"/api/appointments/{reference}/cancel", headers=auth_headers(desk_client))
    assert desk_client.post(url, json={"decision": "confirm"}, headers=staff).status_code == 409


def test_declined_request_shows_the_reason_and_cannot_be_cancelled(desk_client):
    reference = submit(desk_client)
    staff = auth_headers(desk_client, STAFF)
    desk_client.post(
        f"/api/front-desk/requests/{reference}/decision",
        json={"decision": "decline", "note": "Dermatology is closed that week; please choose another date."},
        headers=staff,
    )
    patient = auth_headers(desk_client)
    mine = desk_client.get("/api/appointments/mine", headers=patient).json()[0]
    assert mine["status"] == "declined"
    assert "closed that week" in mine["review_note"]
    assert desk_client.post(f"/api/appointments/{reference}/cancel", headers=patient).status_code == 409


def test_unknown_reference_and_invalid_decision(desk_client):
    staff = auth_headers(desk_client, STAFF)
    assert desk_client.post("/api/front-desk/requests/NH-APT-9999/decision", json={"decision": "confirm"}, headers=staff).status_code == 404
    reference = submit(desk_client)
    bad = desk_client.post(f"/api/front-desk/requests/{reference}/decision", json={"decision": "approve"}, headers=staff)
    assert bad.status_code == 422


def test_chat_status_reports_the_real_confirmed_status(desk_client):
    reference = submit(desk_client)
    desk_client.post(f"/api/front-desk/requests/{reference}/decision", json={"decision": "confirm"}, headers=auth_headers(desk_client, STAFF))

    body = desk_client.post("/api/assistant/message", json={"message": "show my appointments"}, headers=auth_headers(desk_client)).json()
    items = next(card for card in body["cards"] if card["type"] == "appointment_list")["items"]
    assert items[0]["status"] == "confirmed"
