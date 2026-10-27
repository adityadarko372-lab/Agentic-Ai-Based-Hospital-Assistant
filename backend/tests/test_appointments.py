"""Appointment Management (Module 5): validation, persistence, honesty,
duplicate protection and ownership."""

import re
from datetime import timedelta

import pytest

from app.core.clock import today_in_india
from app.db.session import reset_engine
from tests.conftest import PATIENT_B, auth_headers, build_client, valid_appointment

KEY = {"Idempotency-Key": "form-0001-abcdef"}


def submit(client, headers, payload=None, key="form-0001-abcdef"):
    return client.post(
        "/api/appointments", json=payload or valid_appointment(), headers={**headers, "Idempotency-Key": key}
    )


def test_submitted_request_is_saved_as_pending_with_a_reference(client):
    response = submit(client, auth_headers(client))

    assert response.status_code == 201
    body = response.json()
    assert re.fullmatch(r"NH-APT-\d{4}", body["reference"])
    assert body["status"] == "pending"
    assert body["department_name"] == "Cardiology"
    assert body["source"] == "form"
    # Honesty rule: nothing in the response claims a confirmed booking.
    assert "confirm" not in response.text.lower()


def test_requests_are_listed_newest_first(client):
    headers = auth_headers(client)
    first = submit(client, headers, key="form-key-first").json()
    second = submit(client, headers, valid_appointment(department_id="dermatology"), key="form-key-second").json()

    listed = client.get("/api/appointments/mine", headers=headers).json()
    assert [item["reference"] for item in listed] == [second["reference"], first["reference"]]


def test_request_survives_a_backend_restart(database_path):
    with build_client(database_path) as client:
        reference = submit(client, auth_headers(client)).json()["reference"]
    reset_engine()

    with build_client(database_path) as restarted:
        listed = restarted.get("/api/appointments/mine", headers=auth_headers(restarted)).json()
    reset_engine()

    assert [item["reference"] for item in listed] == [reference]
    assert listed[0]["status"] == "pending"


def test_same_idempotency_key_does_not_create_a_duplicate(client):
    headers = auth_headers(client)
    first = submit(client, headers)
    repeat = submit(client, headers)

    assert first.status_code == 201
    assert repeat.status_code == 200
    assert repeat.json()["reference"] == first.json()["reference"]
    assert len(client.get("/api/appointments/mine", headers=headers).json()) == 1


def test_reused_key_with_different_details_is_a_conflict(client):
    headers = auth_headers(client)
    submit(client, headers)
    response = submit(client, headers, valid_appointment(reason="A completely different reason here."))

    assert response.status_code == 409


@pytest.mark.parametrize(
    ("overrides", "field", "message_fragment"),
    [
        ({"preferred_date": today_in_india().isoformat()}, "preferred_date", "from tomorrow"),
        ({"preferred_date": (today_in_india() - timedelta(days=3)).isoformat()}, "preferred_date", "from tomorrow"),
        ({"preferred_date": (today_in_india() + timedelta(days=91)).isoformat()}, "preferred_date", "90 days"),
        ({"preferred_date": "31-12-2026"}, "preferred_date", "valid date"),
        ({"reason": "pain"}, "reason", "at least 10"),
        ({"reason": "x" * 501}, "reason", "under 500"),
        ({"patient_name": "A"}, "patient_name", "full name"),
        ({"patient_name": "Asha <script>"}, "patient_name", "letters"),
        ({"department_id": "brain-surgery"}, "department_id", "from the list"),
        ({"department_id": "emergency"}, "department_id", "does not take appointment"),
    ],
)
def test_invalid_requests_are_rejected_with_a_field_message(client, overrides, field, message_fragment):
    headers = auth_headers(client)
    response = submit(client, headers, valid_appointment(**overrides))

    assert response.status_code == 422
    assert message_fragment in response.json()["field_errors"][field]
    assert client.get("/api/appointments/mine", headers=headers).json() == []


def test_missing_fields_are_reported(client):
    response = submit(client, auth_headers(client), {"department_id": "cardiology"})

    assert response.status_code == 422
    errors = response.json()["field_errors"]
    assert errors["patient_name"] == errors["reason"] == errors["preferred_date"] == "This field is required."


def test_last_allowed_day_is_accepted(client):
    payload = valid_appointment(preferred_date=(today_in_india() + timedelta(days=90)).isoformat())
    assert submit(client, auth_headers(client), payload).status_code == 201


@pytest.mark.parametrize("name", ["आशा वर्मा", "Dr. K. Iyer", "Anne-Marie D'Souza", "கவியா ஐயர்"])
def test_names_in_indian_scripts_and_with_punctuation_are_accepted(client, name):
    assert submit(client, auth_headers(client), valid_appointment(patient_name=name)).status_code == 201


@pytest.mark.parametrize("name", ["Asha 123", "Asha_Verma", "-Asha", "Asha--", "<b>Asha</b>"])
def test_names_with_digits_or_symbols_are_rejected(client, name):
    response = submit(client, auth_headers(client), valid_appointment(patient_name=name))
    assert response.status_code == 422
    assert "patient_name" in response.json()["field_errors"]


def test_whitespace_is_tidied(client):
    payload = valid_appointment(patient_name="  Asha   Verma ", reason="  Follow-up    for my knee pain.  ")
    body = submit(client, auth_headers(client), payload).json()

    assert body["patient_name"] == "Asha Verma"
    assert body["reason"] == "Follow-up for my knee pain."


def test_patients_cannot_see_or_cancel_each_others_requests(client):
    asha = auth_headers(client)
    rohan = auth_headers(client, PATIENT_B)
    reference = submit(client, asha).json()["reference"]

    assert client.get("/api/appointments/mine", headers=rohan).json() == []
    assert client.post(f"/api/appointments/{reference}/cancel", headers=rohan).status_code == 404
    # Asha's request is untouched.
    assert client.get("/api/appointments/mine", headers=asha).json()[0]["status"] == "pending"


def test_same_idempotency_key_from_two_patients_creates_two_requests(client):
    first = submit(client, auth_headers(client))
    second = submit(client, auth_headers(client, PATIENT_B), valid_appointment(patient_name="Rohan Mehta"))

    assert first.status_code == second.status_code == 201
    assert first.json()["reference"] != second.json()["reference"]


def test_pending_request_can_be_cancelled_once(client):
    headers = auth_headers(client)
    reference = submit(client, headers).json()["reference"]

    cancelled = client.post(f"/api/appointments/{reference}/cancel", headers=headers)
    again = client.post(f"/api/appointments/{reference}/cancel", headers=headers)

    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"
    assert again.status_code == 409


def test_submission_and_cancellation_appear_in_activity_without_medical_details(client):
    headers = auth_headers(client)
    reference = submit(client, headers).json()["reference"]
    client.post(f"/api/appointments/{reference}/cancel", headers=headers)

    events = client.get("/api/activity/mine", headers=headers).json()
    assert [event["event_type"] for event in events] == ["appointment.cancelled", "appointment.submitted"]
    assert all(event["reference"] == reference for event in events)
    assert all(event["actor"] == "You" for event in events)
    # The free-text reason is private and is not copied into the history.
    assert "palpitations" not in str(events)


def test_activity_is_private_to_each_patient(client):
    submit(client, auth_headers(client))
    assert client.get("/api/activity/mine", headers=auth_headers(client, PATIENT_B)).json() == []


def test_invalid_idempotency_key_is_rejected(client):
    response = submit(client, auth_headers(client), key="bad key!")
    assert response.status_code == 400
