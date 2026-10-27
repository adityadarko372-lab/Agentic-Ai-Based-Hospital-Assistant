"""Chooses the intent classifier from settings, always falling back to rules.

INTENT_CLASSIFIER=rules        -> RuleBasedIntentClassifier (default)
INTENT_CLASSIFIER=transformer  -> optional trained model (Phase 5). Until it
                                  exists, this falls back to the rules and the
                                  trace says so.
"""

import logging
from functools import lru_cache

from app.agents.intent.classifier import IntentClassifier, RuleBasedIntentClassifier
from app.core.config import get_settings

logger = logging.getLogger("nova_health.intent")


@lru_cache
def get_intent_classifier() -> tuple[IntentClassifier, str | None]:
    """Return (classifier, fallback_note). fallback_note is None when no fallback happened."""
    requested = get_settings().intent_classifier
    if requested == "transformer":
        note = "Trained classifier requested but not installed in this build; using transparent rules."
        logger.warning(note)
        return RuleBasedIntentClassifier(), note
    return RuleBasedIntentClassifier(), None
