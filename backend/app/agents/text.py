"""Small, explainable text helpers shared by the agents.

Matching is done on whole words/phrases, so "ear" does not match "year" and
"cold" does not match "scold".
"""

import re
from functools import lru_cache

_QUOTES = str.maketrans({"’": "'", "‘": "'", "“": '"', "”": '"', "–": "-", "—": "-"})
_SPACES = re.compile(r"\s+")
# Words that, just before a phrase, mean the person is saying they do NOT have it.
NEGATION_WORDS = {"no", "not", "never", "without", "denies", "deny", "don't", "dont", "doesn't", "doesnt", "isn't", "isnt"}
_NEGATION_WINDOW = 3


def normalise(text: str) -> str:
    """Lower-case, straighten quotes and collapse whitespace."""
    return _SPACES.sub(" ", text.translate(_QUOTES).lower()).strip()


@lru_cache(maxsize=4096)
def _phrase_pattern(phrase: str) -> re.Pattern[str]:
    escaped = re.escape(phrase.lower()).replace(r"\ ", r"\s+")
    return re.compile(rf"(?<![a-z0-9]){escaped}(?![a-z0-9])")


def find_phrase(normalised_text: str, phrase: str) -> re.Match[str] | None:
    return _phrase_pattern(phrase).search(normalised_text)


def is_negated(normalised_text: str, match_start: int) -> bool:
    """True if one of the few words before the match is a negation ("no chest pain")."""
    preceding = re.findall(r"[a-z']+", normalised_text[:match_start])[-_NEGATION_WINDOW:]
    return any(word in NEGATION_WORDS for word in preceding)


def find_affirmed_phrases(normalised_text: str, phrases: list[str]) -> tuple[list[str], list[str]]:
    """Return (affirmed, negated) phrases found in the text."""
    affirmed: list[str] = []
    negated: list[str] = []
    for phrase in phrases:
        match = find_phrase(normalised_text, phrase)
        if match is None:
            continue
        (negated if is_negated(normalised_text, match.start()) else affirmed).append(phrase)
    return affirmed, negated


def contains_any(normalised_text: str, phrases: list[str]) -> list[str]:
    return [phrase for phrase in phrases if find_phrase(normalised_text, phrase)]
