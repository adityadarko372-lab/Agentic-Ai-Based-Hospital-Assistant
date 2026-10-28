"""Preliminary Symptom Guidance form (Module 4)."""

import re

import pytest

from app.knowledge import load_care_rules
from tests.conftest import PATIENT_B, auth_headers
from tests.test_agents_routing import ask
from tests.test_agents_safety import DIAGNOSIS_WORDS


def assess(client, headers, **body):
    return client.post("/api/care-navigation/assess", json=body, headers=headers)


def test_options_list_warning_signs_symptoms_and_choices(client):
    body = client.get("/api/care-navigation/options").json()

    assert {item["id"] for item in body["warning_signs"]} == {rule["id"] for rule in load_care_rules()["red_flags"]}
    assert any(item["id"] == "cough" for item in body["symptoms"])
    assert "general_pain" not in {item["id"] for item in body["symptoms"]}
    assert [d["id"] for d in body["durations"]] == ["under_1_day", "1_3_days", "4_7_days", "1_3_weeks", "over_3_weeks"]
    assert [s["id"] for s in body["severities"]] == ["mild", "moderate", "severe"]
    assert body["clinically_reviewed"] is False
    assert "not a diagnosis" in body["disclaimer"]


def test_assessment_requires_sign_in(client):
    assert client.post("/api/care-navigation/assess", json={"symptom_ids": ["cough"]}).status_code == 401


def test_mild_cough_gives_self_care_guidance_and_is_traced(client):
    headers = auth_headers(client)
    response = assess(client, headers, symptom_ids=["cough"], duration="1_3_days", severity="mild", age_group="adult")

    assert response.status_code == 200
    body = response.json()
    assert body["assessment"]["level"] == "self_care"
    assert body["assessment"]["department_id"] == "general-medicine"
    run = body["run"]
    assert run["selected_agent"] == "Care Navigation Agent"
    assert run["classifier_method"] == "form"
    assert [s["action"] for s in run["steps"]] == ["receive_form", "check_safety", "apply_care_rules", "record_outcome"]
    # Visible in the Agent Activity history and the dashboard activity feed.
    assert client.get("/api/activity/runs", headers=headers).json()[0]["id"] == run["id"]
    event = client.get("/api/activity/mine", headers=headers).json()[0]
    assert event["event_type"] == "care.assessment"
    assert event["actor"] == "Care Navigation Agent"


@pytest.mark.parametrize("flag", [rule["id"] for rule in load_care_rules()["red_flags"]])
def test_every_ticked_warning_sign_gives_emergency_guidance_without_other_answers(client, flag):
    body = assess(client, auth_headers(client), symptom_ids=[flag]).json()

    assessment = body["assessment"]
    assert assessment["level"] == "emergency"
    assert assessment["can_request_appointment"] is False
    assert "112" in [entry["number"] for entry in assessment["emergency_numbers"]]
    assert body["run"]["outcome_status"] == "emergency_escalation"
    assert body["run"]["steps"][1]["status"] == "warning"


def test_warning_sign_in_free_text_overrides_mild_answers(client):
    body = assess(client, auth_headers(client), symptom_ids=["cough"], free_text="also some chest pain", duration="1_3_days", severity="mild").json()
    assert body["assessment"]["level"] == "emergency"


def test_self_harm_points_to_tele_manas(client):
    numbers = [n["number"] for n in assess(client, auth_headers(client), symptom_ids=["self_harm"]).json()["assessment"]["emergency_numbers"]]
    assert numbers == ["112", "14416"]


@pytest.mark.parametrize(
    ("form", "chat_message"),
    [
        ({"symptom_ids": ["cough"], "duration": "1_3_days", "severity": "mild"}, "I have had a mild cough for 2 days"),
        ({"symptom_ids": ["joint_pain"], "free_text": "knee pain", "duration": "1_3_weeks", "severity": "moderate"}, "moderate knee pain for 2 weeks"),
        ({"symptom_ids": ["abdominal_pain"], "duration": "under_1_day", "severity": "severe"}, "severe stomach pain since this morning"),
        ({"symptom_ids": ["cough"], "duration": "1_3_days", "severity": "mild", "age_group": "child"}, "my son has had a mild cough for 2 days"),
        ({"symptom_ids": ["chest_pain"]}, "I have chest pain"),
    ],
)
def test_form_and_chat_give_the_same_guidance(client, form, chat_message):
    """The form and the assistant use the same care engine (plan, Phase 4 acceptance criterion)."""
    headers = auth_headers(client)
    form_result = assess(client, headers, **form).json()["assessment"]
    chat = ask(client, headers, chat_message)
    card = next(c for c in chat["cards"] if c["type"] in ("care_guidance", "emergency"))
    if card["type"] == "emergency":
        assert form_result["level"] == "emergency"
    else:
        assert card["assessment"]["level"] == form_result["level"]
        assert card["assessment"]["department_id"] == form_result["department_id"]


def test_long_duration_and_risk_factors_raise_the_level(client):
    headers = auth_headers(client)
    long_cough = assess(client, headers, symptom_ids=["cough"], duration="over_3_weeks", severity="mild").json()["assessment"]
    older = assess(client, headers, symptom_ids=["cold"], duration="1_3_days", severity="mild", age_group="older_adult").json()["assessment"]
    pregnant = assess(client, headers, symptom_ids=["vomiting"], duration="1_3_days", severity="mild", pregnant=True).json()["assessment"]
    baby = assess(client, headers, symptom_ids=["fever"], duration="under_1_day", severity="mild", age_group="infant").json()["assessment"]

    assert long_cough["level"] == "see_doctor_soon"
    assert older["level"] == "routine"
    assert pregnant["level"] == "urgent_same_day"
    assert baby["level"] == "urgent_same_day"
    assert baby["department_id"] == "emergency"


def test_unrecognised_description_asks_for_more(client):
    body = assess(client, auth_headers(client), free_text="something feels off").json()
    assert body["assessment"]["level"] is None
    assert body["run"]["outcome_status"] == "needs_input"


@pytest.mark.parametrize(
    ("payload", "field", "fragment"),
    [
        ({}, "symptom_ids", "at least one symptom"),
        ({"free_text": "ok"}, "symptom_ids", "at least one symptom"),
        ({"symptom_ids": ["made_up"]}, "symptom_ids", "from the list"),
        ({"symptom_ids": ["cough"], "duration": "forever"}, "duration", "one of the options"),
        ({"symptom_ids": ["cough"], "severity": "terrible"}, "severity", "one of the options"),
        ({"symptom_ids": ["cough"], "free_text": "x" * 501}, "free_text", "under 500"),
    ],
)
def test_invalid_form_input_is_rejected(client, payload, field, fragment):
    response = assess(client, auth_headers(client), **payload)
    assert response.status_code == 422
    assert fragment in response.json()["field_errors"][field]


def test_free_text_is_not_copied_into_the_activity_feed(client):
    headers = auth_headers(client)
    assess(client, headers, symptom_ids=["skin"], free_text="itchy rash on my left elbow", duration="4_7_days", severity="mild")
    assert "elbow" not in str(client.get("/api/activity/mine", headers=headers).json())


def test_form_runs_are_private(client):
    body = assess(client, auth_headers(client), symptom_ids=["cough"], duration="1_3_days", severity="mild").json()
    rohan = auth_headers(client, PATIENT_B)
    assert client.get(f"/api/activity/runs/{body['run']['id']}", headers=rohan).status_code == 404


@pytest.mark.parametrize(
    "form",
    [
        {"symptom_ids": ["fever", "body_ache"], "duration": "4_7_days", "severity": "moderate"},
        {"symptom_ids": ["skin"], "duration": "1_3_weeks", "severity": "mild"},
        {"symptom_ids": ["low_mood"], "duration": "over_3_weeks", "severity": "moderate"},
        {"symptom_ids": ["chest_pain"]},
    ],
)
def test_form_guidance_never_names_a_condition_or_medicine(client, form):
    text = str(assess(client, auth_headers(client), **form).json()["assessment"])
    cleaned = re.sub(r"not a diagnosis", "", text, flags=re.IGNORECASE)
    assert not DIAGNOSIS_WORDS.search(cleaned)
