"""Optional trained intent classifier (DistilBERT, fine-tuned in Phase 5).

Selected with INTENT_CLASSIFIER=transformer. The model is trained by
model/intent_classifier/train.py and loaded from
model/artifacts/intent_classifier/ on the CPU (one short message needs no GPU).

It is a hybrid with the transparent rules, chosen by
model/intent_classifier/compare_policies.py ("rules_first_cautious"):

1. Rules guard: a request for a diagnosis, a prescription or a dose (rule
   label out_of_scope, confidence >= 0.75) is always refused by the rules.
2. When the rules are confident (>= the Supervisor's 0.45), they decide.
   Their reasons stay readable in the Agent Activity panel.
3. Otherwise the trained model decides, except that a model "out_of_scope"
   becomes a clarifying question instead of a refusal (the model was too
   quick to refuse real hospital questions in testing).
The Safety Gate runs before any classifier.
"""

import json
import threading
from pathlib import Path

from app.agents.intent.classifier import INTENTS, IntentPrediction, RuleBasedIntentClassifier

# Rule refusals at or above this confidence override the model.
GUARD_CONFIDENCE = 0.75
# Same value as supervisor.CONFIDENCE_THRESHOLD (not imported, to avoid a cycle).
RULES_CONFIDENT = 0.45


class TransformerIntentClassifier:
    name = "transformer"

    def __init__(self, model_dir: Path) -> None:
        import torch
        from transformers import AutoModelForSequenceClassification, AutoTokenizer

        labels = json.loads((model_dir / "labels.json").read_text(encoding="utf-8"))
        if sorted(labels) != sorted(INTENTS):
            raise ValueError("The trained model's labels do not match the current intents; retrain it.")
        self._torch = torch
        self._labels = labels
        self._tokenizer = AutoTokenizer.from_pretrained(str(model_dir))
        self._model = AutoModelForSequenceClassification.from_pretrained(str(model_dir)).to("cpu").eval()
        self._rules = RuleBasedIntentClassifier()
        self._lock = threading.Lock()

    def predict_model_only(self, normalised_text: str) -> IntentPrediction:
        """The fine-tuned model's own answer (used for evaluation)."""
        with self._lock, self._torch.no_grad():
            encoded = self._tokenizer(normalised_text, truncation=True, max_length=64, return_tensors="pt")
            probabilities = self._torch.softmax(self._model(**encoded).logits[0], dim=-1).tolist()
        scores = {label: round(p, 4) for label, p in zip(self._labels, probabilities)}
        ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
        top_intent, top_p = ranked[0]
        evidence = [f"model: {label} {p:.2f}" for label, p in ranked[:3]]
        return IntentPrediction(top_intent, round(top_p, 2), "transformer", evidence, scores)

    def predict(self, normalised_text: str) -> IntentPrediction:
        rules = self._rules.predict(normalised_text)
        if rules.intent == "out_of_scope" and rules.confidence >= GUARD_CONFIDENCE:
            return IntentPrediction(
                "out_of_scope", rules.confidence, "rules_guard", ["safety rule kept by the rules guard", *rules.evidence], rules.scores
            )
        if rules.intent != "unknown" and rules.confidence >= RULES_CONFIDENT:
            return IntentPrediction(rules.intent, rules.confidence, "hybrid_rules", rules.evidence, rules.scores)

        model = self.predict_model_only(normalised_text)
        if model.intent == "out_of_scope":
            return IntentPrediction(
                "unknown", 0.0, "hybrid_clarify", ["model suggested out_of_scope; asking the patient instead", *model.evidence], model.scores
            )
        return model
