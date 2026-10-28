"""Chooses the intent classifier from settings, always falling back to rules.

INTENT_CLASSIFIER=rules        -> RuleBasedIntentClassifier (default)
INTENT_CLASSIFIER=transformer  -> the optional fine-tuned DistilBERT model
                                  (model/artifacts/intent_classifier). If the
                                  model or its libraries are missing, the rules
                                  are used and the trace says why.
"""

import logging
from functools import lru_cache

from app.agents.intent.classifier import IntentClassifier, RuleBasedIntentClassifier
from app.core.config import get_settings

logger = logging.getLogger("nova_health.intent")


@lru_cache
def get_intent_classifier() -> tuple[IntentClassifier, str | None]:
    """Return (classifier, fallback_note). fallback_note is None when no fallback happened."""
    settings = get_settings()
    if settings.intent_classifier != "transformer":
        return RuleBasedIntentClassifier(), None

    model_dir = settings.intent_model_dir
    if not (model_dir / "labels.json").exists():
        note = f"Trained classifier requested but not found in {model_dir.name}/; using transparent rules."
    else:
        try:
            from app.agents.intent.transformer import TransformerIntentClassifier

            return TransformerIntentClassifier(model_dir), None
        except ImportError as error:
            note = f"Trained classifier requested but {error.name} is not installed; using transparent rules."
        except Exception as error:  # noqa: BLE001 - never crash the assistant over an optional model
            logger.exception("Could not load the trained intent classifier")
            note = f"Trained classifier could not be loaded ({type(error).__name__}); using transparent rules."
    logger.warning(note)
    return RuleBasedIntentClassifier(), note
