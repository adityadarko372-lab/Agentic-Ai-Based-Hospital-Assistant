"""Safety Gate: the first check on every assistant message.

1. Emergency warning signs (from care_rules.json). If any is present, the
   message goes straight to emergency guidance, whatever else it says, and no
   further questions are asked first.
2. Attempts to override the assistant's rules or reach other people's data
   (prompt injection). These are refused; the request is never forwarded.

Both checks are fixed, readable rules. No AI model can switch them off.
"""

from dataclasses import dataclass, field
from typing import Literal

from app.agents.text import find_affirmed_phrases, find_phrase
from app.knowledge import load_care_rules

# Phrases that try to change the assistant's rules or access data it must not give.
INJECTION_PATTERNS: list[str] = [
    "ignore previous instructions",
    "ignore all previous instructions",
    "ignore your instructions",
    "ignore all instructions",
    "ignore the rules",
    "ignore your rules",
    "disregard your instructions",
    "forget your instructions",
    "forget your rules",
    "system prompt",
    "developer mode",
    "jailbreak",
    "you are now",
    "pretend you are a doctor",
    "act as a doctor",
    "act as my doctor",
    "you are a doctor now",
    "bypass",
    "override the safety",
    "disable safety",
    "other patients",
    "other patient's",
    "another patient's",
    "all patients",
    "every patient",
    "everyone's appointments",
    "all appointments in the database",
    "show me the database",
    "drop table",
    "admin access",
    "mark it as confirmed",
    "mark my appointment as confirmed",
    "set the status to confirmed",
    "change the status to confirmed",
]

EmergencyNumber = dict[str, str]


@dataclass
class RedFlagMatch:
    id: str
    label: str
    matched_phrase: str
    numbers: list[str]


@dataclass
class SafetyResult:
    kind: Literal["ok", "emergency", "injection"]
    red_flags: list[RedFlagMatch] = field(default_factory=list)
    negated_mentions: list[str] = field(default_factory=list)
    injection_phrases: list[str] = field(default_factory=list)

    @property
    def emergency_numbers(self) -> list[EmergencyNumber]:
        labels = load_care_rules()["emergency_numbers"]
        ordered: list[str] = []
        for flag in self.red_flags:
            for number in flag.numbers:
                if number not in ordered:
                    ordered.append(number)
        return [{"number": number, "label": labels[number]} for number in ordered]


def detect_red_flags(normalised_text: str) -> tuple[list[RedFlagMatch], list[str]]:
    """Return affirmed warning signs and any negated mentions ("no chest pain")."""
    matches: list[RedFlagMatch] = []
    negated_all: list[str] = []
    for rule in load_care_rules()["red_flags"]:
        affirmed, negated = find_affirmed_phrases(normalised_text, rule["phrases"])
        negated_all.extend(negated)
        if not affirmed:
            continue
        # Some signs only count together with another word (fever + stiff neck).
        required = rule.get("requires_any")
        if required and not any(find_phrase(normalised_text, word) for word in required):
            continue
        matches.append(RedFlagMatch(rule["id"], rule["label"], affirmed[0], rule["numbers"]))
    return matches, negated_all


def check_message(normalised_text: str) -> SafetyResult:
    red_flags, negated = detect_red_flags(normalised_text)
    if red_flags:
        # Emergency wins over everything, including injection attempts.
        return SafetyResult("emergency", red_flags=red_flags, negated_mentions=negated)

    injection = [phrase for phrase in INJECTION_PATTERNS if find_phrase(normalised_text, phrase)]
    if injection:
        return SafetyResult("injection", injection_phrases=injection, negated_mentions=negated)

    return SafetyResult("ok", negated_mentions=negated)
