"""Compare ways of combining the rules and the trained model.

    backend\\.venv\\Scripts\\python.exe model\\intent_classifier\\compare_policies.py

Policies (all keep the Safety Gate and the rules guard for medicine/diagnosis):
  rules         transparent rules only (default)
  model         trained model only
  rules_first   rules when they are confident (>= 0.45), otherwise the model
  rules_first_cautious
                as rules_first, but when the model says "out_of_scope" and
                the rules did not, ask the patient instead of refusing

The policy is CHOSEN ON TEST SET A ONLY (fewest wrongly routed messages, then
most correct ones). Test set B is reported afterwards as the unbiased check.
Writes model/intent_classifier/policy_results.json.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.agents.intent.classifier import IntentPrediction, RuleBasedIntentClassifier  # noqa: E402
from app.agents.intent.transformer import GUARD_CONFIDENCE, TransformerIntentClassifier  # noqa: E402
from app.agents.supervisor import CONFIDENCE_THRESHOLD  # noqa: E402
from app.agents.text import normalise  # noqa: E402

HERE = Path(__file__).parent
MODEL_DIR = ROOT / "model" / "artifacts" / "intent_classifier"


def combine(policy: str, rules: IntentPrediction, model: IntentPrediction) -> IntentPrediction:
    rules_confident = rules.intent != "unknown" and rules.confidence >= CONFIDENCE_THRESHOLD
    # The medicine / diagnosis guard applies to every policy.
    if rules.intent == "out_of_scope" and rules.confidence >= GUARD_CONFIDENCE:
        return rules
    if policy == "rules":
        return rules
    if policy == "model":
        return model
    if rules_confident:
        return rules
    if policy == "rules_first_cautious" and model.intent == "out_of_scope":
        return IntentPrediction("unknown", 0.0, "hybrid", ["model said out_of_scope; asking instead"])
    return model


def score(policy: str, rows: list[tuple[str, IntentPrediction, IntentPrediction]]) -> dict:
    routed = correct = 0
    for gold, rules, model in rows:
        prediction = combine(policy, rules, model)
        if prediction.intent != "unknown" and prediction.confidence >= CONFIDENCE_THRESHOLD:
            routed += 1
            correct += prediction.intent == gold
    n = len(rows)
    return {"n": n, "routed_correct": correct, "routed_wrong": routed - correct, "asked_to_clarify": n - routed,
            "correct_rate": round(correct / n, 3)}


def main() -> None:
    rules_clf = RuleBasedIntentClassifier()
    model_clf = TransformerIntentClassifier(MODEL_DIR)
    policies = ["rules", "model", "rules_first", "rules_first_cautious"]
    results = {}
    for set_name, filename in (("A", "test_set.json"), ("B", "test_set_b.json")):
        examples = json.loads((HERE / filename).read_text(encoding="utf-8"))["examples"]
        rows = []
        for example in examples:
            text = normalise(example["text"])
            rows.append((example["label"], rules_clf.predict(text), model_clf.predict_model_only(text)))
        results[set_name] = {policy: score(policy, rows) for policy in policies}

    # A wrongly routed message costs twice as much as a clarifying question
    # (the patient gets an unhelpful answer and must rephrase). "Fewest wrong"
    # alone always picks the rules, because they abstain on most messages.
    for block in results.values():
        for r in block.values():
            r["utility"] = r["routed_correct"] - 2 * r["routed_wrong"]
    chosen = max(policies, key=lambda p: results["A"][p]["utility"])
    output = {"selection": "max(correct - 2 x wrong) on set A", "chosen_on_set_A": chosen, "results": results}
    (HERE / "policy_results.json").write_text(json.dumps(output, indent=2), encoding="utf-8")
    for set_name in ("A", "B"):
        for policy in policies:
            r = results[set_name][policy]
            print(f"set {set_name} {policy:22s} correct {r['routed_correct']:3d}/{r['n']}  wrong {r['routed_wrong']:2d}  "
                  f"clarify {r['asked_to_clarify']:2d}  utility {r['utility']:3d}")
    print(f"chosen on set A: {chosen}")


if __name__ == "__main__":
    main()
