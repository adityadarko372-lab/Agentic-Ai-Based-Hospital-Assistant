"""Phase 5 (optional): local-LLM rewording is narrow, guarded and never required."""

import urllib.error

import pytest

from app.agents import phrasing
from app.core.config import get_settings
from app.db.session import reset_engine
from tests.conftest import auth_headers, build_client

ORIGINAL = "Here is what to bring to your appointment at Nova Health. Please arrive 15 minutes early."


@pytest.mark.parametrize(
    ("rewrite", "problem"),
    [
        ("Please bring these things and come about 15 minutes early to Nova Health.", None),
        ("Please arrive 30 minutes early.", "added numbers"),
        ("Here is what to bring to Nova Health. Please come a little early.", "dropped numbers"),
        ("Bring these, take a paracetamol tablet, and arrive 15 minutes early.", "added medical"),
        ("You are definitely confirmed; arrive 15 minutes early.", "added medical or promise"),
        ("Arrive 15 minutes early. See www.example.com for details.", "added a link"),
        ("", "empty"),
    ],
)
def test_rewrite_guard(rewrite, problem):
    result = phrasing.check_rewrite(ORIGINAL, rewrite)
    if problem is None:
        assert result is None
    else:
        assert result and problem in result


@pytest.fixture
def llm_client(database_path, monkeypatch):
    monkeypatch.setenv("LLM_PHRASING_ENABLED", "true")
    with build_client(database_path) as client:
        yield client
    reset_engine()
    monkeypatch.undo()
    get_settings.cache_clear()


def ask(client, message):
    response = client.post("/api/assistant/message", json={"message": message}, headers=auth_headers(client))
    assert response.status_code == 200, response.text
    return response.json()


def step(body, action):
    return next(s for s in body["run"]["steps"] if s["action"] == action)


def test_off_by_default_never_calls_ollama(client, monkeypatch):
    def fail(*_args, **_kwargs):
        raise AssertionError("Ollama must not be called when the flag is off")

    monkeypatch.setattr(phrasing, "_call_ollama", fail)
    body = ask(client, "What should I bring to my appointment?")
    assert "optional AI phrasing is off" in step(body, "compose_reply")["detail"]


def test_safe_rewrite_is_used_and_traced(llm_client, monkeypatch):
    rewrite = "Sure! Here's what to bring to Nova Health. Please come 15 minutes early to register at the Main Reception."
    monkeypatch.setattr(phrasing, "_call_ollama", lambda *a, **k: rewrite)
    body = ask(llm_client, "What should I bring to my appointment?")
    assert body["reply"] == rewrite
    assert body["cards"][0]["type"] == "checklist"  # cards are untouched
    assert "Reworded by local model" in step(body, "rephrase_reply")["detail"]


def test_unsafe_rewrite_keeps_the_template(llm_client, monkeypatch):
    monkeypatch.setattr(phrasing, "_call_ollama", lambda *a, **k: "Bring your ID and arrive 45 minutes early.")
    body = ask(llm_client, "What should I bring to my appointment?")
    assert body["reply"].startswith("Here is what to bring")
    assert "rewrite rejected" in step(body, "rephrase_reply")["detail"]


def test_ollama_down_keeps_the_template(llm_client, monkeypatch):
    def down(*_a, **_k):
        raise urllib.error.URLError("connection refused")

    monkeypatch.setattr(phrasing, "_call_ollama", down)
    body = ask(llm_client, "What should I bring to my appointment?")
    assert body["reply"].startswith("Here is what to bring")
    assert step(body, "rephrase_reply")["status"] == "fallback"


def test_emergency_and_appointment_replies_are_never_reworded(llm_client, monkeypatch):
    calls = []
    monkeypatch.setattr(phrasing, "_call_ollama", lambda *a, **k: calls.append(a) or "reworded")
    emergency = ask(llm_client, "I have severe chest pain")
    assert emergency["outcome_status"] == "emergency_escalation"
    booking = ask(llm_client, "I want to book an appointment")
    assert booking["agent"] == "Appointment Agent"
    assert calls == []
    assert "keep their exact template wording" in step(emergency, "rephrase_reply")["detail"]


def test_non_local_ollama_url_is_refused(database_path, monkeypatch):
    monkeypatch.setenv("LLM_PHRASING_ENABLED", "true")
    monkeypatch.setenv("OLLAMA_URL", "https://llm.example.com")
    monkeypatch.setattr(phrasing, "_call_ollama", lambda *a, **k: (_ for _ in ()).throw(AssertionError("must not call")))
    with build_client(database_path) as client:
        body = ask(client, "What should I bring to my appointment?")
    reset_engine()
    monkeypatch.undo()
    get_settings.cache_clear()
    assert step(body, "rephrase_reply")["status"] == "blocked"


def test_whole_hours_may_be_shortened():
    original = "Cardiology is at Block B, First Floor. Hours: Mon–Sat, 9:00 AM – 4:00 PM (Ext. 2201)."
    assert phrasing.check_rewrite(original, "Cardiology is on the first floor of Block B, open 9 AM to 4 PM Mon–Sat (Ext. 2201).") is None
    assert "dropped" in phrasing.check_rewrite(original, "Cardiology is in Block B, open 9 AM to 4 PM.")
