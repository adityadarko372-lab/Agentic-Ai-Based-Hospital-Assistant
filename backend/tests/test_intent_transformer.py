"""Phase 5 (optional): selecting the trained intent classifier safely."""

import json

import pytest

from app.agents.intent import factory
from app.agents.intent.classifier import INTENTS, RuleBasedIntentClassifier
from app.agents.intent.transformer import TransformerIntentClassifier
from app.agents.text import normalise
from app.core.config import get_settings


@pytest.fixture
def transformer_requested(monkeypatch, tmp_path):
    monkeypatch.setenv("INTENT_CLASSIFIER", "transformer")
    monkeypatch.setenv("INTENT_MODEL_DIR", str(tmp_path / "intent_model"))
    get_settings.cache_clear()
    factory.get_intent_classifier.cache_clear()
    yield tmp_path / "intent_model"
    monkeypatch.undo()
    get_settings.cache_clear()
    factory.get_intent_classifier.cache_clear()


def test_missing_model_falls_back_to_rules_with_a_note(transformer_requested):
    classifier, note = factory.get_intent_classifier()
    assert isinstance(classifier, RuleBasedIntentClassifier)
    assert note and "not found" in note


def test_broken_model_falls_back_to_rules(transformer_requested):
    transformer_requested.mkdir()
    (transformer_requested / "labels.json").write_text(json.dumps(list(INTENTS)), encoding="utf-8")
    classifier, note = factory.get_intent_classifier()
    assert isinstance(classifier, RuleBasedIntentClassifier)
    assert note and "using transparent rules" in note


def test_rules_guard_keeps_medicine_and_diagnosis_refusals():
    """The guard runs before the model, so it can be tested without loading one."""
    guard = TransformerIntentClassifier.__new__(TransformerIntentClassifier)
    guard._rules = RuleBasedIntentClassifier()  # noqa: SLF001
    for message in ("what is the dose of paracetamol", "Do I have diabetes?", "can you prescribe antibiotics"):
        prediction = guard.predict(normalise(message))
        assert prediction.intent == "out_of_scope"
        assert prediction.method == "rules_guard"
