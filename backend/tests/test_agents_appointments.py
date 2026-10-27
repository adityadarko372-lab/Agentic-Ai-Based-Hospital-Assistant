"""Appointment Agent: multi-turn booking, honest status, cancellation."""

from datetime import date, timedelta

import pytest

from app.agents.date_parser import parse_preferred_date
from app.core.clock import today_in_india
from tests.conftest import auth_headers, valid_appointment
from tests.test_agents_routing import ask


def converse(client, headers, messages):
    conversation_id, replies = None, []
    for message in messages:
        body = ask(client, headers, message, conversation_id)
        conversation_id = body["conversation_id"]
        replies.append(body)
    return replies


def test_spec_demo_booking_through_chat(client):
    """partial implementation.md, Module 3 example: 'I want to book an appointment'."""
    headers = auth_headers(client)
    replies = converse(client, headers, ["I want to book an appointment", "Orthopaedics", "next monday", "Knee pain while climbing stairs", "yes"])

    assert [r["agent"] for r in replies] == ["Appointment Agent"] * 5
    assert [r["outcome_status"] for r in replies] == ["needs_input"] * 4 + ["action_completed"]
    # Routing step of a follow-up message explains that it continues the task.
    follow_up_route = next(s for s in replies[1]["run"]["steps"] if s["action"] == "route_request")
    assert "continues an unfinished appointment request" in follow_up_route["detail"]
    # Follow-ups are recorded as routed by conversation context, not as "unknown".
    for reply in replies[1:]:
        assert reply["intent"] == "continue_appointment_booking"
        assert reply["method"] == "conversation_context"
        assert reply["run"]["classifier_method"] == "conversation_context"

    final = replies[-1]
    submitted = next(card for card in final["cards"] if card["type"] == "appointment_submitted")["appointment"]
    assert submitted["status"] == "pending"
    assert submitted["source"] == "assistant"
    assert submitted["department_id"] == "orthopaedics"
    assert submitted["patient_name"] == "Asha Verma"
    assert final["reference"] == submitted["reference"]
    assert "not yet confirmed" in final["reply"]
    assert "save_request" in [s["action"] for s in final["run"]["steps"]]

    # Saved through the same service as the form: visible in "My requests".
    mine = client.get("/api/appointments/mine", headers=headers).json()
    assert [item["reference"] for item in mine] == [submitted["reference"]]
    events = client.get("/api/activity/mine", headers=headers).json()
    assert events[0]["actor"] == "Appointment Agent"
    assert events[0]["event_type"] == "appointment.submitted"


def test_details_in_the_first_message_are_used(client):
    replies = converse(client, auth_headers(client), ["Book a cardiology appointment for next monday because of palpitations"])

    draft = next(card for card in replies[0]["cards"] if card["type"] == "appointment_draft")
    assert draft["ready"] is True
    assert draft["details"]["department_id"] == "cardiology"
    assert draft["details"]["reason"] == "Palpitations"


def test_nothing_is_saved_before_yes_and_no_discards_the_draft(client):
    headers = auth_headers(client)
    replies = converse(client, headers, ["Book a cardiology appointment for next monday because of palpitations", "no"])

    assert replies[-1]["pending_task"] is None
    assert client.get("/api/appointments/mine", headers=headers).json() == []


def test_a_second_yes_does_not_create_a_duplicate(client):
    headers = auth_headers(client)
    converse(client, headers, ["Book a cardiology appointment for next monday because of palpitations", "yes", "yes"])
    assert len(client.get("/api/appointments/mine", headers=headers).json()) == 1


def test_stop_abandons_the_booking(client):
    headers = auth_headers(client)
    replies = converse(client, headers, ["I want to book an appointment", "stop"])

    assert "Nothing was submitted" in replies[-1]["reply"]
    assert replies[-1]["pending_task"] is None


@pytest.mark.parametrize(("date_message", "fragment"), [("today", "from tomorrow"), ("in 20 weeks", "90 days")])
def test_invalid_dates_are_explained_and_asked_again(client, date_message, fragment):
    replies = converse(client, auth_headers(client), ["Book an appointment with dermatology", date_message])

    assert fragment in replies[-1]["reply"]
    assert replies[-1]["pending_task"] == "appointment_booking"


def test_departments_without_appointments_are_refused(client):
    replies = converse(client, auth_headers(client), ["I want to book an appointment", "emergency department"])
    assert "does not take appointment requests" in replies[-1]["reply"]


def test_short_reason_is_asked_again(client):
    replies = converse(client, auth_headers(client), ["Book an appointment with dermatology", "tomorrow", "rash"])
    assert "at least 10 characters" in replies[-1]["reply"]


def test_hospital_question_during_booking_keeps_the_draft(client):
    headers = auth_headers(client)
    replies = converse(client, headers, ["I want to book an appointment", "What should I bring to my appointment?", "Cardiology"])

    assert replies[1]["agent"] == "Patient Assistance Agent"
    assert "unfinished appointment request" in replies[1]["reply"]
    assert replies[1]["pending_task"] is None  # this reply itself asks nothing
    assert replies[2]["agent"] == "Appointment Agent"
    assert "What date" in replies[2]["reply"]


def test_status_shows_real_stored_status_and_never_claims_confirmation(client):
    headers = auth_headers(client)
    client.post("/api/appointments", json=valid_appointment(), headers={**headers, "Idempotency-Key": "form-status-0001"})

    body = ask(client, headers, "Is my appointment confirmed yet?")
    assert body["agent"] == "Appointment Agent"
    items = next(card for card in body["cards"] if card["type"] == "appointment_list")["items"]
    assert [item["status"] for item in items] == ["pending"]
    assert "has not confirmed" in body["reply"]


def test_cancel_through_chat_asks_first(client):
    headers = auth_headers(client)
    created = client.post("/api/appointments", json=valid_appointment(), headers={**headers, "Idempotency-Key": "form-cancel-0001"}).json()

    replies = converse(client, headers, ["cancel my appointment", "yes"])
    assert replies[0]["outcome_status"] == "needs_input"
    assert replies[0]["pending_task"] == "cancel_confirmation"
    assert replies[1]["outcome_status"] == "action_completed"
    assert client.get("/api/appointments/mine", headers=headers).json()[0]["status"] == "cancelled"
    events = client.get("/api/activity/mine", headers=headers).json()
    assert events[0]["event_type"] == "appointment.cancelled" and events[0]["reference"] == created["reference"]


def test_cancel_with_no_keeps_the_request(client):
    headers = auth_headers(client)
    client.post("/api/appointments", json=valid_appointment(), headers={**headers, "Idempotency-Key": "form-keep-00001"})
    converse(client, headers, ["cancel my appointment", "no"])
    assert client.get("/api/appointments/mine", headers=headers).json()[0]["status"] == "pending"


def test_cannot_cancel_another_patients_request_by_reference(client):
    from tests.conftest import PATIENT_B

    asha = auth_headers(client)
    created = client.post("/api/appointments", json=valid_appointment(), headers={**asha, "Idempotency-Key": "form-asha-00001"}).json()
    body = ask(client, auth_headers(client, PATIENT_B), f"cancel {created['reference']}")

    assert "couldn't find" in body["reply"]
    assert client.get("/api/appointments/mine", headers=asha).json()[0]["status"] == "pending"


TODAY = date(2026, 10, 27)  # a Tuesday


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("tomorrow", date(2026, 10, 28)),
        ("day after tomorrow", date(2026, 10, 29)),
        ("next monday", date(2026, 11, 2)),
        ("tuesday", date(2026, 11, 3)),
        ("in 3 days", date(2026, 10, 30)),
        ("in 2 weeks", date(2026, 11, 10)),
        ("05/11/2026", date(2026, 11, 5)),
        ("5-11", date(2026, 11, 5)),
        ("2026-12-01", date(2026, 12, 1)),
        ("5th november", date(2026, 11, 5)),
        ("nov 20", date(2026, 11, 20)),
        ("3 jan", date(2027, 1, 3)),
    ],
)
def test_date_parser_understands_common_formats(text, expected):
    assert parse_preferred_date(text, TODAY)[0] == expected


def test_date_parser_returns_nothing_for_text_without_a_date():
    assert parse_preferred_date("knee pain while climbing stairs", TODAY) == (None, None)
    assert parse_preferred_date("31/02/2026", TODAY)[0] is None


def test_today_in_india_is_used_for_relative_dates():
    assert parse_preferred_date("tomorrow", today_in_india())[0] == today_in_india() + timedelta(days=1)
