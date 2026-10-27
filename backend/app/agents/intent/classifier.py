"""Intent classifier interface and the default transparent rule classifier.

Any classifier (rules today, an optional trained model in Phase 5) returns the
same `IntentPrediction`, so the Supervisory Agent does not care which one is
running. The rule classifier is fully explainable: every point of its score
comes from a listed pattern, and the matched patterns are returned as evidence
and shown in the Agent Activity panel.

How the score works
-------------------
1. Each intent has patterns with a weight (1 = weak hint, 3 = strong signal).
2. An intent's score is the sum of the weights of its matched patterns.
3. confidence = strength x dominance
      strength  = min(top_score / 3, 1)        (how strong the best signal is)
      dominance = top_score / (top + second)   (how clearly it beats the runner-up)
   e.g. top 3, runner-up 0  -> 1.00;  top 2, runner-up 0 -> 0.67;
        top 2, runner-up 2  -> 0.33 (ambiguous, so the assistant asks).
   The runner-up is the best intent from a *different group*: hospital_info
   and department_query are both answered by the Patient Assistance Agent,
   so a tie between them is not a real ambiguity.
"""

import re
from dataclasses import dataclass, field
from typing import Protocol

from app.agents.text import contains_any, find_phrase
from app.knowledge import load_care_rules, load_department_keywords

INTENTS = (
    "greeting",
    "help",
    "hospital_info",
    "department_query",
    "appointment_book",
    "appointment_status",
    "appointment_cancel",
    "symptom_report",
    "out_of_scope",
)


# Intents in the same group are not treated as competitors (see docstring).
INTENT_GROUPS = {
    "greeting": "conversation",
    "help": "conversation",
    "hospital_info": "information",
    "department_query": "information",
    "appointment_book": "booking",
    "appointment_status": "appointment_records",
    "appointment_cancel": "appointment_records",
    "symptom_report": "care",
    "out_of_scope": "out_of_scope",
}

# "how do I book ..." is a question about the process, not a booking request.
_NOT_A_PROCESS_QUESTION = r"(?<!how do i )(?<!how can i )(?<!how should i )(?<!how to )(?<!process to )(?<!steps to )"


@dataclass
class IntentPrediction:
    intent: str
    confidence: float
    method: str
    evidence: list[str] = field(default_factory=list)
    scores: dict[str, float] = field(default_factory=dict)


class IntentClassifier(Protocol):
    """Anything that can label a message with one of INTENTS."""

    name: str

    def predict(self, normalised_text: str) -> IntentPrediction: ...


# (regex, weight). Regexes run on normalised (lower-case) text.
_RULES: dict[str, list[tuple[str, float]]] = {
    "greeting": [
        (r"^(hi|hello|hey|hii+|namaste|namaskar|good (morning|afternoon|evening))\b", 3),
        (r"^(thanks|thank you|thank u|thx|ok thanks|great,? thanks)\b", 3),
        (r"^(bye|goodbye|see you)\b", 3),
    ],
    "help": [
        (r"\bwhat can you (do|help)", 3),
        (r"\bhow can you help\b", 3),
        (r"\bwho are you\b", 3),
        (r"^help\b", 3),
        (r"\bwhat (are|is) (nova|this assistant)", 2),
    ],
    "hospital_info": [
        (r"\b(what|which) (documents|things|papers)\b", 2),
        (r"\bwhat (should|do|must) i (bring|carry)", 3),
        (r"\b(bring|carry) (to|for|with)\b", 2),
        (r"\bvisiting (hours|time|timings)\b", 3),
        (r"\b(visit|see) (a|my) (patient|relative|family member)\b", 2),
        (r"\b(opening|opd|working|clinic) (hours|time|timings)\b", 3),
        (r"\b(timings?|hours)\b", 1),
        (r"\b(timings?|hours|schedule) (of|for)\b", 2),
        (r"\b(when|what time) (is|does|do|are)\b.*\b(open|close|available)", 3),
        (r"\bhow (do|can|should) i (book|make|get|request) (an |a )?appointment", 3),
        (r"\b(process|steps|procedure) (to|for) (book|booking|request)", 3),
        (r"\bwhere (is|are|can i (find|get|do|go))\b", 2),
        (r"\b(hospital )?services\b", 2),
        (r"\b(help ?desk|reception|address|location|parking|canteen)\b", 2),
        (r"\b(lab|laboratory|blood test|pharmacy|chemist)\b", 1),
        (r"\b(insurance|aadhaar|id proof)\b", 2),
        (r"\b(emergency department|emergency ward|casualty)\b", 2),
    ],
    "department_query": [
        (r"\bwhich (department|doctor|specialist|clinic)\b", 3),
        (r"\b(what|which) department\b", 3),
        (r"\b(right|correct|best) (department|doctor|specialist)\b", 3),
        (r"\b(who|where) should i (see|go|visit|consult)\b", 3),
        (r"\b(departments?|specialities|specialties)\b", 1),
        (r"\bfor (a |my )?consultation\b", 1),
    ],
    "appointment_book": [
        (_NOT_A_PROCESS_QUESTION + r"\b(book|schedule|fix|make|get|need|want|request) (an? |my )?(new )?(appointment|consultation|slot|visit)\b", 3),
        (_NOT_A_PROCESS_QUESTION + r"\b(book|schedule)\b.*\b(appointment|consultation|doctor)\b", 2),
        (r"\b(want|need|like) to (see|consult|meet) (a |the )?(doctor|specialist|cardiologist|dermatologist)", 3),
        (r"\bnew appointment\b", 3),
        (r"\b(appointment) (with|for|in|at)\b", 1),
        (_NOT_A_PROCESS_QUESTION + r"\b(book|booking)\b", 1),
    ],
    "appointment_status": [
        (r"\bstatus\b", 3),
        (r"\b(show|list|view|check|see) (me )?(my |all my )?(appointments?|requests?|bookings?)\b", 3),
        (r"\b(my|any) (appointment|booking)? ?requests\b", 2),
        (r"\b(is|has) my (appointment|request|booking)\b", 3),
        (r"\b(confirmed|approved|accepted) yet\b", 3),
        (r"\bwhat happened to my (appointment|request)\b", 3),
        (r"\bnh-apt-\d{4}\b", 1),
    ],
    "appointment_cancel": [
        (r"\bcancel\b", 3),
        (r"\b(withdraw|call off|delete) (my )?(appointment|request|booking)\b", 3),
        (r"\b(don't|do not|no longer) need (the|my|an?) (appointment|request)\b", 3),
    ],
    "out_of_scope": [
        (r"\b(weather|cricket|movie|song|joke|recipe|stock|bitcoin|football|politics|election)\b", 3),
        (r"\b(write|solve) (a |my )?(poem|essay|code|homework|program)\b", 3),
        (r"\b(capital of|who won|tell me a story)\b", 3),
        (r"\b(prescribe|prescription for|which medicine|what medicine|dosage|dose of|how many tablets)\b", 3),
        (r"\b(do i have|is it|could it be|is this) (cancer|diabetes|covid|dengue|malaria|a heart attack|serious)\b", 3),
        (r"\bdiagnos(e|is)\b", 3),
    ],
}

# How much a recognised symptom phrase adds to "symptom_report".
_SYMPTOM_WEIGHT = 2.0
# Strong first-person symptom framing.
_SYMPTOM_FRAMING = re.compile(r"\b(i have|i've got|i am having|i'm having|i feel|i'm feeling|suffering from|my \w+ (hurts|is paining|aches)|since (yesterday|\d+ days?))\b")


@dataclass
class _Compiled:
    pattern: re.Pattern[str]
    source: str
    weight: float


class RuleBasedIntentClassifier:
    """Weighted keyword / regex rules. Transparent and needs no model files."""

    name = "rules"

    def __init__(self) -> None:
        self._rules = {
            intent: [_Compiled(re.compile(source), source, weight) for source, weight in rules]
            for intent, rules in _RULES.items()
        }
        self._symptom_phrases = [
            phrase for symptom in load_care_rules()["symptoms"] for phrase in symptom["phrases"]
        ]
        departments = load_department_keywords()["departments"]
        self._department_aliases = [alias for record in departments.values() for alias in record["aliases"]]

    def predict(self, normalised_text: str) -> IntentPrediction:
        scores: dict[str, float] = {intent: 0.0 for intent in INTENTS}
        evidence: dict[str, list[str]] = {intent: [] for intent in INTENTS}

        for intent, rules in self._rules.items():
            for rule in rules:
                match = rule.pattern.search(normalised_text)
                if match:
                    scores[intent] += rule.weight
                    evidence[intent].append(f'"{match.group(0).strip()}" (+{rule.weight:g})')

        symptoms = contains_any(normalised_text, self._symptom_phrases)
        # "pain" alone is weak; specific phrases are stronger.
        specific = [s for s in symptoms if s not in {"pain", "paining", "hurts", "hurting", "ache", "aching", "sore"}]
        if specific:
            scores["symptom_report"] += _SYMPTOM_WEIGHT
            evidence["symptom_report"].append(f"symptom words {specific[:3]} (+{_SYMPTOM_WEIGHT:g})")
        elif symptoms:
            scores["symptom_report"] += 1
            evidence["symptom_report"].append(f"symptom words {symptoms[:3]} (+1)")
        if symptoms and _SYMPTOM_FRAMING.search(normalised_text):
            scores["symptom_report"] += 1
            evidence["symptom_report"].append("describes own symptoms (+1)")

        # Naming a department alone ("cardiology?") is a weak navigation hint.
        aliases = [alias for alias in self._department_aliases if find_phrase(normalised_text, alias)]
        if aliases:
            scores["department_query"] += 1
            evidence["department_query"].append(f"department named {aliases[:2]} (+1)")

        # A question about which department, asked with symptoms, is navigation.
        if scores["department_query"] >= 3 and scores["symptom_report"] > 0:
            scores["department_query"] += 1
            evidence["department_query"].append("asks where to go for a symptom (+1)")

        ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
        top_intent, top = ranked[0]
        if top == 0:
            return IntentPrediction("unknown", 0.0, self.name, ["no known words matched"], scores)

        top_group = INTENT_GROUPS[top_intent]
        second = max((score for intent, score in ranked[1:] if INTENT_GROUPS[intent] != top_group), default=0.0)
        strength = min(top / 3.0, 1.0)
        dominance = top / (top + second)
        confidence = round(strength * dominance, 2)
        return IntentPrediction(top_intent, confidence, self.name, evidence[top_intent], scores)
