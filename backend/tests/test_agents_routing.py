"""Supervisory Agent routing: a table of realistic messages and where each must go.

The first four are the example questions from partial implementation.md.
"""

import pytest

from tests.conftest import auth_headers

ROUTING_TABLE = [
    # (message, expected intent, expected agent)
    ("Which department should I visit for a consultation?", "department_query", "Patient Assistance Agent"),
    ("What should I bring to my appointment?", "hospital_info", "Patient Assistance Agent"),
    ("How do I book an appointment?", "hospital_info", "Patient Assistance Agent"),
    ("Where can I find hospital services?", "hospital_info", "Patient Assistance Agent"),
    ("Where is cardiology?", "hospital_info", "Patient Assistance Agent"),
    ("What are the OPD timings?", "hospital_info", "Patient Assistance Agent"),
    ("What are the visiting hours?", "hospital_info", "Patient Assistance Agent"),
    ("Which department for knee pain?", "department_query", "Patient Assistance Agent"),
    ("Which doctor should I see for a skin rash?", "department_query", "Patient Assistance Agent"),
    ("where is the pharmacy", "hospital_info", "Patient Assistance Agent"),
    ("what time does the lab open", "hospital_info", "Patient Assistance Agent"),
    ("where is the emergency department", "hospital_info", "Patient Assistance Agent"),
    ("is there parking", "hospital_info", "Patient Assistance Agent"),
    ("What documents do I need to carry?", "hospital_info", "Patient Assistance Agent"),
    ("I want to book an appointment", "appointment_book", "Appointment Agent"),
    ("I need to see a dermatologist", "appointment_book", "Appointment Agent"),
    ("Book a cardiology appointment for next monday", "appointment_book", "Appointment Agent"),
    ("Can I get an appointment with orthopaedics?", "appointment_book", "Appointment Agent"),
    ("schedule a consultation please", "appointment_book", "Appointment Agent"),
    ("what is the status of my appointment", "appointment_status", "Appointment Agent"),
    ("show my appointments", "appointment_status", "Appointment Agent"),
    ("has my request been confirmed yet", "appointment_status", "Appointment Agent"),
    ("cancel my appointment", "appointment_cancel", "Appointment Agent"),
    ("I no longer need the appointment", "appointment_cancel", "Appointment Agent"),
    ("I have had a mild cough for 3 days", "symptom_report", "Care Navigation Agent"),
    ("I have a headache", "symptom_report", "Care Navigation Agent"),
    ("I've had back pain for 3 weeks", "symptom_report", "Care Navigation Agent"),
    ("my baby has a fever", "symptom_report", "Care Navigation Agent"),
    ("I feel dizzy since yesterday", "symptom_report", "Care Navigation Agent"),
    ("hello", "greeting", "Supervisory Agent"),
    ("Good morning", "greeting", "Supervisory Agent"),
    ("thanks", "greeting", "Supervisory Agent"),
    ("what can you do", "help", "Supervisory Agent"),
    ("what's the weather today", "out_of_scope", "Supervisory Agent"),
    ("write a poem about the sea", "out_of_scope", "Supervisory Agent"),
    ("what medicine should I take for fever", "out_of_scope", "Supervisory Agent"),
    ("do i have diabetes", "out_of_scope", "Supervisory Agent"),
    ("can you diagnose my rash", "out_of_scope", "Supervisory Agent"),
]


def ask(client, headers, message, conversation_id=None):
    response = client.post("/api/assistant/message", json={"message": message, "conversation_id": conversation_id}, headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


@pytest.mark.parametrize(("message", "intent", "agent"), ROUTING_TABLE)
def test_message_is_routed_to_the_right_agent(client, message, intent, agent):
    body = ask(client, auth_headers(client), message)

    assert body["intent"] == intent, body["run"]["steps"]
    assert body["agent"] == agent
    assert body["confidence"] >= 0.45
    assert body["method"] == "rules"


@pytest.mark.parametrize("message", ["pain", "asdfgh", "appointment", "hmm ok so"])
def test_unclear_messages_get_a_clarifying_question(client, message):
    body = ask(client, auth_headers(client), message)

    assert body["outcome_status"] == "clarification"
    assert body["agent"] == "Supervisory Agent"
    assert body["suggestions"]


def test_every_run_is_traced_in_order(client):
    headers = auth_headers(client)
    body = ask(client, headers, "What should I bring to my appointment?")
    actions = [step["action"] for step in body["run"]["steps"]]

    assert actions[:4] == ["receive_message", "check_safety", "classify_intent", "route_request"]
    assert actions[-2:] == ["compose_reply", "record_outcome"]
    assert "lookup_directory" in actions
    classify = next(step for step in body["run"]["steps"] if step["action"] == "classify_intent")
    assert classify["data"]["evidence"], "the rule classifier must show which words it matched"
    # The same run is readable from the activity history.
    runs = client.get("/api/activity/runs", headers=headers).json()
    assert runs[0]["id"] == body["run_id"]
    assert runs[0]["selected_agent"] == "Patient Assistance Agent"
    detail = client.get(f"/api/activity/runs/{body['run_id']}", headers=headers).json()
    assert [s["order"] for s in detail["steps"]] == list(range(1, len(detail["steps"]) + 1))


def test_answers_name_their_source(client):
    body = ask(client, auth_headers(client), "What are the visiting hours?")
    assert any("demo directory" in source for source in body["sources"])


def test_unknown_hospital_question_is_not_guessed(client):
    body = ask(client, auth_headers(client), "Where can I find the hospital's cafeteria menu for vegans?")

    assert body["agent"] == "Patient Assistance Agent"
    assert body["outcome_status"] == "information_unavailable"
    assert "won't guess" in body["reply"]


def test_assistant_requires_sign_in(client):
    assert client.post("/api/assistant/message", json={"message": "hello"}).status_code == 401


def test_empty_and_overlong_messages_are_rejected(client):
    headers = auth_headers(client)
    empty = client.post("/api/assistant/message", json={"message": "   "}, headers=headers)
    long = client.post("/api/assistant/message", json={"message": "a" * 1001}, headers=headers)

    assert empty.status_code == long.status_code == 422
    assert empty.json()["field_errors"]["message"] == "Please type a message."


def test_other_patients_cannot_use_a_conversation_or_read_runs(client):
    from tests.conftest import PATIENT_B

    asha = auth_headers(client)
    body = ask(client, asha, "hello")
    rohan = auth_headers(client, PATIENT_B)

    response = client.post("/api/assistant/message", json={"message": "hi", "conversation_id": body["conversation_id"]}, headers=rohan)
    assert response.status_code == 404
    assert client.get(f"/api/activity/runs/{body['run_id']}", headers=rohan).status_code == 404
    assert client.get("/api/activity/runs", headers=rohan).json() == []
    assert client.get(f"/api/assistant/conversations/{body['conversation_id']}", headers=rohan).status_code == 404


def test_conversation_history_can_be_reloaded(client):
    headers = auth_headers(client)
    first = ask(client, headers, "hello")
    ask(client, headers, "What should I bring?", first["conversation_id"])

    history = client.get(f"/api/assistant/conversations/{first['conversation_id']}", headers=headers).json()
    assert [run["user_message"] for run in history] == ["hello", "What should I bring?"]


def test_assistant_runs_appear_in_recent_activity_without_the_message_text(client):
    headers = auth_headers(client)
    ask(client, headers, "What should I bring to my appointment?")

    events = client.get("/api/activity/mine", headers=headers).json()
    assert events[0]["actor"] == "Patient Assistance Agent"
    assert "What should I bring" not in events[0]["summary"]
