"""Phase 5 (optional): Health Information Agent over NIH MedQuAD.

The real index needs sentence-transformers and a built index, so these tests
use a fake retriever. They check the safety-relevant behaviour: off by
default, honest when unavailable, a similarity threshold, citations, and that
the Safety Gate and the diagnosis/medicine refusal still come first.
"""

import pytest

from app.agents import health_info_agent
from app.agents.intent.classifier import RuleBasedIntentClassifier
from app.agents.text import normalise
from app.core.config import get_settings
from app.db.session import reset_engine
from app.health_info import retriever as retriever_module
from app.health_info.medquad import MIN_ANSWER_CHARS, dedupe, excerpt, parse_document
from app.health_info.retriever import SearchHit
from tests.conftest import auth_headers, build_client

ANSWER = "Asthma is a chronic disease that affects your airways. " * 4

SAMPLE_XML = f"""<?xml version="1.0" encoding="UTF-8"?>
<Document id="0000001" source="MPlusHealthTopics" url="https://medlineplus.gov/asthma.html">
<Focus>Asthma</Focus>
<QAPairs>
<QAPair pid="1"><Question qid="0000001-1" qtype="information">What is (are) Asthma ?</Question><Answer>{ANSWER}</Answer></QAPair>
<QAPair pid="2"><Question qid="0000001-2" qtype="symptoms">What are the symptoms of Asthma ?</Question><Answer></Answer></QAPair>
<QAPair pid="3"><Question qid="0000001-3" qtype="dosage">What is the dose of Asthma inhalers ?</Question><Answer>{ANSWER}</Answer></QAPair>
<QAPair pid="4"><Question qid="0000001-4" qtype="treatment">How to treat Asthma ?</Question><Answer>See your doctor.</Answer></QAPair>
</QAPairs>
</Document>"""

RECORD = {
    "id": "0000001-1",
    "focus": "Asthma",
    "question": "What is Asthma?",
    "qtype": "information",
    "answer": ANSWER.strip(),
    "source": "MPlusHealthTopics",
    "url": "https://medlineplus.gov/asthma.html",
}


class FakeRetriever:
    name = "fake"

    def __init__(self, score: float) -> None:
        self.score = score
        self.queries: list[str] = []

    def search(self, query: str, k: int = 3) -> list[SearchHit]:
        self.queries.append(query)
        return [SearchHit(RECORD, self.score)]


# ---------- dataset preparation ----------
def test_parser_keeps_answered_pairs_and_drops_medicine_questions_and_stubs():
    records = parse_document(SAMPLE_XML)
    assert [r.id for r in records] == ["0000001-1"]
    record = records[0]
    assert record.question == "What is Asthma?"
    assert record.focus == "Asthma"
    assert record.source == "MPlusHealthTopics"
    assert record.url.startswith("https://")
    assert len(record.answer) >= MIN_ANSWER_CHARS


def test_parser_drops_whole_medicine_topics():
    xml = SAMPLE_XML.replace("<Focus>Asthma</Focus>", "<Focus>Diabetes Medicines</Focus>")
    assert parse_document(xml) == []


def test_dedupe_and_excerpt():
    records = parse_document(SAMPLE_XML)
    assert len(dedupe(records + records)) == 1
    short = excerpt("First sentence here. " * 80, limit=200)
    assert len(short) <= 200 and short.endswith(".")


def test_parser_refuses_entity_declarations():
    bomb = '<?xml version="1.0"?><!DOCTYPE d [<!ENTITY a "aaaa">]><Document><Focus>&a;</Focus></Document>'
    with pytest.raises(Exception):
        parse_document(bomb)


# ---------- intent rules ----------
@pytest.mark.parametrize(
    ("message", "intent"),
    [
        ("What is asthma?", "health_info"),
        ("how is malaria spread", "health_info"),
        ("What are the symptoms of diabetes?", "health_info"),
        ("what causes high blood pressure", "health_info"),
        ("is tuberculosis contagious", "health_info"),
        ("tell me about glaucoma", "health_info"),
        # Existing meanings are unchanged.
        ("Do I have diabetes?", "out_of_scope"),
        ("what is the dose of paracetamol", "out_of_scope"),
        ("What is the status of my appointment request?", "appointment_status"),
        ("What is nova?", "help"),
        ("I have had a mild cough for 3 days", "symptom_report"),
        ("Which department should I visit for a consultation?", "department_query"),
    ],
)
def test_rule_classifier_health_info_intent(message, intent):
    assert RuleBasedIntentClassifier().predict(normalise(message)).intent == intent


# ---------- agent behaviour ----------
@pytest.fixture
def info_client(database_path, monkeypatch):
    monkeypatch.setenv("HEALTH_INFO_ENABLED", "true")
    retriever_module.get_retriever.cache_clear()
    with build_client(database_path) as client:
        yield client
    reset_engine()
    monkeypatch.undo()
    get_settings.cache_clear()
    retriever_module.get_retriever.cache_clear()


def ask(client, message):
    response = client.post("/api/assistant/message", json={"message": message}, headers=auth_headers(client))
    assert response.status_code == 200, response.text
    return response.json()


def test_switched_off_by_default_says_unavailable(client):
    body = ask(client, "What is asthma?")
    assert body["agent"] == "Health Information Agent"
    assert body["outcome_status"] == "information_unavailable"
    assert body["cards"] == []
    step = next(s for s in body["run"]["steps"] if s["action"] == "search_medquad")
    assert "switched off" in step["detail"] and step["status"] == "fallback"


def test_missing_index_says_unavailable(info_client, monkeypatch, tmp_path):
    monkeypatch.setattr(retriever_module, "index_dir", lambda: tmp_path / "no-index")
    retriever_module.get_retriever.cache_clear()
    body = ask(info_client, "What is asthma?")
    assert body["outcome_status"] == "information_unavailable"
    step = next(s for s in body["run"]["steps"] if s["action"] == "search_medquad")
    assert "index not built" in step["detail"]


def test_confident_match_is_cited_and_labelled(info_client, monkeypatch):
    fake = FakeRetriever(score=0.82)
    monkeypatch.setattr(health_info_agent, "get_retriever", lambda: fake)
    body = ask(info_client, "What is asthma?")
    assert body["outcome_status"] == "answered"
    card = body["cards"][0]
    assert card["type"] == "health_info"
    assert card["title"] == "Asthma"
    assert "not medical advice" in card["disclaimer"]
    assert "CC BY 4.0" in card["license"]
    assert "medlineplus.gov" in body["sources"][0]
    assert "not medical advice" in body["reply"]
    assert fake.queries == ["What is asthma?"]


def test_weak_match_is_not_shown(info_client, monkeypatch):
    monkeypatch.setattr(health_info_agent, "get_retriever", lambda: FakeRetriever(score=0.31))
    body = ask(info_client, "What is quantum chromodynamics?")
    assert body["outcome_status"] == "information_unavailable"
    assert body["cards"] == []
    assert "won't guess" in body["reply"]


def test_safety_gate_and_refusals_still_come_first(info_client, monkeypatch):
    fake = FakeRetriever(score=0.95)
    monkeypatch.setattr(health_info_agent, "get_retriever", lambda: fake)
    emergency = ask(info_client, "I have chest pain and I can't breathe, what causes this")
    assert emergency["outcome_status"] == "emergency_escalation"
    refused = ask(info_client, "Do I have diabetes?")
    assert refused["outcome_status"] == "refused"
    assert fake.queries == []


def test_health_endpoint_reports_what_is_really_active(client):
    features = client.get("/api/health").json()["features"]
    assert features["intent_classifier_active"] == "rules"
    assert features["health_info_enabled"] is False
    assert isinstance(features["health_info_index_present"], bool)
