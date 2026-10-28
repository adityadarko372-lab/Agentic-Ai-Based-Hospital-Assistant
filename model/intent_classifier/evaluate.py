"""Compare the rule classifier and the trained model on the hand-written test set.

    backend\\.venv\\Scripts\\python.exe model\\intent_classifier\\evaluate.py

For each classifier it reports, on model/intent_classifier/test_set.json:
- accuracy and macro-F1 of the top label ("unknown" counts as wrong)
- routing behaviour with the Supervisor's threshold (0.45): how many messages
  are routed, how many of those are correct, how many get a clarifying question
- per-intent F1 and every mistake
Writes model/intent_classifier/results.json. The trained model is adopted
only if it beats the rules here; see docs/phase-reports/phase-5-optional-enhancements.md.
"""

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.agents.intent.classifier import INTENTS, RuleBasedIntentClassifier  # noqa: E402
from app.agents.intent.transformer import TransformerIntentClassifier  # noqa: E402
from app.agents.supervisor import CONFIDENCE_THRESHOLD  # noqa: E402
from app.agents.text import normalise  # noqa: E402

TEST_SET = Path(__file__).with_name("test_set.json")
MODEL_DIR = ROOT / "model" / "artifacts" / "intent_classifier"


def f1_per_label(golds: list[str], preds: list[str]) -> dict[str, float]:
    result = {}
    for label in INTENTS:
        tp = sum(1 for g, p in zip(golds, preds) if g == p == label)
        fp = sum(1 for g, p in zip(golds, preds) if p == label and g != label)
        fn = sum(1 for g, p in zip(golds, preds) if g == label and p != label)
        if tp + fp + fn:
            result[label] = round(2 * tp / (2 * tp + fp + fn), 3)
    return result


def run(classifier, examples: list[dict]) -> dict:
    golds, preds, mistakes = [], [], []
    routed = routed_correct = clarified = 0
    started = time.perf_counter()
    for example in examples:
        prediction = classifier.predict(normalise(example["text"]))
        golds.append(example["label"])
        preds.append(prediction.intent)
        confident = prediction.intent != "unknown" and prediction.confidence >= CONFIDENCE_THRESHOLD
        if confident:
            routed += 1
            routed_correct += prediction.intent == example["label"]
        else:
            clarified += 1
        if prediction.intent != example["label"]:
            mistakes.append({"text": example["text"], "expected": example["label"], "got": prediction.intent, "confidence": prediction.confidence, "method": prediction.method})
    per_label = f1_per_label(golds, preds)
    n = len(examples)
    return {
        "examples": n,
        "accuracy": round(sum(g == p for g, p in zip(golds, preds)) / n, 3),
        "macro_f1": round(sum(per_label.values()) / len(per_label), 3),
        "routed": routed,
        "routed_correct": routed_correct,
        "routed_wrong": routed - routed_correct,
        "asked_to_clarify": clarified,
        "ms_per_message": round((time.perf_counter() - started) * 1000 / n, 1),
        "f1_per_intent": per_label,
        "mistakes": mistakes,
    }


class _ModelOnly:
    def __init__(self, model: TransformerIntentClassifier) -> None:
        self._model = model

    def predict(self, text: str):
        return self._model.predict_model_only(text)


TEST_SETS = {
    # A: written first; its round-1 mistakes informed the round-2 changes.
    "A": TEST_SET,
    # B: written after round 1, before round 2 results; never used for decisions.
    "B": Path(__file__).with_name("test_set_b.json"),
}


def main() -> None:
    classifiers: dict = {"rules": RuleBasedIntentClassifier()}
    results: dict = {"confidence_threshold": CONFIDENCE_THRESHOLD, "test_sets": {}}
    if (MODEL_DIR / "labels.json").exists():
        model = TransformerIntentClassifier(MODEL_DIR)
        model.predict("warm up")
        # "model_only": the fine-tuned DistilBERT on its own.
        # "hybrid": what INTENT_CLASSIFIER=transformer actually runs (see transformer.py).
        classifiers["model_only"] = _ModelOnly(model)
        classifiers["hybrid"] = model
        log = MODEL_DIR / "training_log.json"
        if log.exists():
            results["training"] = {k: v for k, v in json.loads(log.read_text(encoding="utf-8")).items() if k != "labels"}
    for set_name, path in TEST_SETS.items():
        if not path.exists():
            continue
        examples = json.loads(path.read_text(encoding="utf-8"))["examples"]
        block = {"file": str(path.relative_to(ROOT))}
        for name, classifier in classifiers.items():
            block[name] = run(classifier, examples)
            r = block[name]
            print(f"set {set_name} {name:12s} n={r['examples']} accuracy {r['accuracy']:.3f}  macro-F1 {r['macro_f1']:.3f}  "
                  f"routed {r['routed']} (wrong {r['routed_wrong']})  clarify {r['asked_to_clarify']}  {r['ms_per_message']} ms/msg")
        results["test_sets"][set_name] = block
    Path(__file__).with_name("results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
