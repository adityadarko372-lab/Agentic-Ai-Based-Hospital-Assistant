"""Care-navigation rules engine (shared by the Care Navigation Agent in chat
and the Symptom Guidance form in Phase 4, so both always agree).

It answers one question: "how soon, and where, should this person seek care?"
It never names a condition, never suggests a medicine and never says that
someone is fine. Every decision is written to `reasons`, so the result can
be explained step by step.

Levels, lowest to highest:
    self_care < routine < see_doctor_soon < urgent_same_day < emergency

Rules, applied in order:
 1. Any emergency warning sign            -> emergency (stop here)
 2. Each recognised symptom has a level   -> take the highest
 3. Lasting more than 7 days              -> at least routine
    Lasting 3 weeks or more               -> at least see_doctor_soon
 4. Described as severe                   -> one level higher (max urgent_same_day)
 5. Baby under 1 with fever               -> urgent_same_day; any baby -> at least see_doctor_soon
    Pregnant with stomach pain / vomiting -> urgent_same_day
    Older adult, pregnant or long-term condition -> at least routine
 6. Department: same-day care -> Emergency Department (appointment requests
    start tomorrow); otherwise the symptom's department, with Paediatrics for
    children and Obstetrics & Gynaecology during pregnancy.
"""

import re
from dataclasses import dataclass, field
from typing import Literal

from app.agents.safety_gate import RedFlagMatch, detect_red_flags
from app.agents.text import contains_any, find_affirmed_phrases, find_phrase, normalise
from app.knowledge import load_care_rules, load_hospital_info

Level = Literal["self_care", "routine", "see_doctor_soon", "urgent_same_day", "emergency"]
LEVEL_ORDER: list[Level] = ["self_care", "routine", "see_doctor_soon", "urgent_same_day", "emergency"]
Severity = Literal["mild", "moderate", "severe"]
AgeGroup = Literal["infant", "child", "adult", "older_adult"]

_GENERIC_PAIN = "general_pain"


@dataclass
class CareInput:
    text: str = ""
    symptom_ids: list[str] = field(default_factory=list)
    duration_days: float | None = None
    severity: Severity | None = None
    age_group: AgeGroup | None = None
    pregnant: bool | None = None
    long_term_condition: bool | None = None


@dataclass
class CareAssessment:
    level: Level | None
    label: str
    explanation: str
    next_steps: list[str]
    department_id: str | None
    department_name: str | None
    can_request_appointment: bool
    matched_symptoms: list[dict[str, str]]
    red_flags: list[dict[str, str]]
    emergency_numbers: list[dict[str, str]]
    support_numbers: list[dict[str, str]]
    reasons: list[str]
    understood: dict[str, object]
    needs_more_info: list[str]
    disclaimer: str
    rules_version: str
    clinically_reviewed: bool


# ---------- reading details from free text ----------
_NUMBER = r"(\d+(?:\.\d+)?|a|an|one|two|three|four|five|six|seven|ten)"
_WORD_NUMBERS = {"a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "ten": 10}
_DURATION = re.compile(rf"\b(?:for|since|from|past|last)?\s*(?:the\s+)?{_NUMBER}\s*(hour|hours|hr|hrs|day|days|week|weeks|month|months)\b")
_UNIT_DAYS = {"hour": 1 / 24, "hours": 1 / 24, "hr": 1 / 24, "hrs": 1 / 24, "day": 1, "days": 1, "week": 7, "weeks": 7, "month": 30, "months": 30}


def _parse_duration(text: str) -> tuple[float | None, str | None]:
    if match := _DURATION.search(text):
        amount_text = match.group(1)
        amount = _WORD_NUMBERS.get(amount_text) or float(amount_text)
        return amount * _UNIT_DAYS[match.group(2)], match.group(0).strip()
    for phrase, days in (
        ("since yesterday", 1.0),
        ("since last night", 1.0),
        ("since this morning", 0.5),
        ("since today", 0.5),
        ("started today", 0.5),
        ("a few days", 3.0),
        ("couple of days", 2.0),
        ("since last week", 7.0),
        ("a long time", 30.0),
    ):
        if find_phrase(text, phrase):
            return days, phrase
    return None, None


def _parse_severity(text: str) -> tuple[Severity | None, str | None]:
    for severity, words in (
        ("severe", ["severe", "unbearable", "very bad", "excruciating", "worst", "very painful", "intense", "extreme"]),
        ("mild", ["mild", "slight", "slightly", "a little", "minor"]),
        ("moderate", ["moderate", "medium"]),
    ):
        if found := contains_any(text, words):
            return severity, found[0]  # type: ignore[return-value]
    return None, None


def _parse_age_group(text: str) -> tuple[AgeGroup | None, str | None]:
    if found := contains_any(text, ["my baby", "infant", "newborn", "months old", "month old", "new born"]):
        return "infant", found[0]
    if match := re.search(r"\b(\d{1,3}) ?(?:years?|yrs?|y) ?old\b", text):
        age = int(match.group(1))
        group: AgeGroup = "child" if age < 16 else "older_adult" if age >= 65 else "adult"
        return group, match.group(0)
    if found := contains_any(text, ["my child", "my son", "my daughter", "my kid", "toddler", "my little one"]):
        return "child", found[0]
    if found := contains_any(text, ["elderly", "my grandfather", "my grandmother", "senior citizen"]):
        return "older_adult", found[0]
    return None, None


# ---------- the engine ----------
def _level_index(level: Level) -> int:
    return LEVEL_ORDER.index(level)


def _at_least(current: Level, minimum: Level) -> Level:
    return minimum if _level_index(current) < _level_index(minimum) else current


def _department_name(department_id: str | None) -> tuple[str | None, bool]:
    if department_id is None:
        return None, False
    for department in load_hospital_info()["departments"]:
        if department["id"] == department_id:
            return department["name"], bool(department["accepts_appointments"])
    return None, False


def _number_entries(numbers: list[str]) -> list[dict[str, str]]:
    labels = load_care_rules()["emergency_numbers"]
    return [{"number": number, "label": labels[number]} for number in numbers]


def evaluate(care_input: CareInput) -> CareAssessment:
    rules = load_care_rules()
    text = normalise(care_input.text)
    reasons: list[str] = []
    understood: dict[str, object] = {}

    # Free-text details fill in anything the form did not provide.
    duration_days, duration_text = care_input.duration_days, None
    if duration_days is None:
        duration_days, duration_text = _parse_duration(text)
    severity, severity_text = care_input.severity, None
    if severity is None:
        severity, severity_text = _parse_severity(text)
    age_group, age_text = care_input.age_group, None
    if age_group is None:
        age_group, age_text = _parse_age_group(text)
    pregnant = care_input.pregnant
    if pregnant is None:
        affirmed, _ = find_affirmed_phrases(text, ["pregnant", "pregnancy"])
        pregnant = bool(affirmed) or None

    if duration_days is not None:
        understood["duration"] = duration_text or f"{duration_days:g} days"
    if severity:
        understood["severity"] = severity_text or severity
    if age_group:
        understood["age_group"] = age_text or age_group
    if pregnant:
        understood["pregnant"] = True
    if care_input.long_term_condition:
        understood["long_term_condition"] = True

    # Rule 1: warning signs.
    red_flags: list[RedFlagMatch]
    red_flags, _negated = detect_red_flags(text)
    known_flag_ids = {rule["id"]: rule for rule in rules["red_flags"]}
    for symptom_id in care_input.symptom_ids:
        if symptom_id in known_flag_ids and symptom_id not in {flag.id for flag in red_flags}:
            rule = known_flag_ids[symptom_id]
            red_flags.append(RedFlagMatch(rule["id"], rule["label"], "selected on the form", rule["numbers"]))

    if red_flags:
        level_info = rules["levels"]["emergency"]
        numbers: list[str] = []
        for flag in red_flags:
            numbers.extend(number for number in flag.numbers if number not in numbers)
        reasons.append("Warning sign found: " + ", ".join(flag.label for flag in red_flags) + ".")
        next_steps = list(level_info["next_steps"])
        if "14416" in numbers:
            next_steps.insert(
                0,
                "You do not have to face this alone. Call 112 if you are in immediate danger, or Tele-MANAS "
                "on 14416 (free, 24×7) to talk to a trained counsellor now. If you can, stay with someone you trust.",
            )
        name, _ = _department_name("emergency")
        return CareAssessment(
            level="emergency",
            label=level_info["label"],
            explanation=level_info["explanation"],
            next_steps=next_steps,
            department_id="emergency",
            department_name=name,
            can_request_appointment=False,
            matched_symptoms=[],
            red_flags=[{"id": f.id, "label": f.label, "matched": f.matched_phrase} for f in red_flags],
            emergency_numbers=_number_entries(numbers),
            support_numbers=[],
            reasons=reasons,
            understood=understood,
            needs_more_info=[],
            disclaimer=rules["disclaimer"],
            rules_version=rules["version"],
            clinically_reviewed=bool(rules["clinically_reviewed"]),
        )

    # Rule 2: recognised symptoms.
    by_id = {symptom["id"]: symptom for symptom in rules["symptoms"]}
    matched: dict[str, str] = {}
    for symptom in rules["symptoms"]:
        affirmed, _ = find_affirmed_phrases(text, symptom["phrases"])
        if affirmed:
            matched[symptom["id"]] = affirmed[0]
    for symptom_id in care_input.symptom_ids:
        if symptom_id in by_id:
            matched.setdefault(symptom_id, "selected on the form")
    # "fever" is part of "high fever"; keep the more specific one.
    if "high_fever" in matched:
        matched.pop("fever", None)
    # A generic word like "pain" adds nothing when a specific symptom is named.
    if len(matched) > 1:
        matched.pop(_GENERIC_PAIN, None)

    needs_more_info: list[str] = []
    if not matched:
        return CareAssessment(
            level=None,
            label="Tell us a little more",
            explanation="I could not recognise the symptoms described, so I cannot suggest a level of care yet.",
            next_steps=[
                "Describe the main symptom in simple words (for example: fever, cough, knee pain, rash).",
                "If you feel very unwell or something feels seriously wrong, call 112 or 108 now.",
            ],
            department_id=None,
            department_name=None,
            can_request_appointment=False,
            matched_symptoms=[],
            red_flags=[],
            emergency_numbers=_number_entries(["112", "108"]),
            support_numbers=[],
            reasons=["No known symptom words were found."],
            understood=understood,
            needs_more_info=["symptoms"],
            disclaimer=rules["disclaimer"],
            rules_version=rules["version"],
            clinically_reviewed=bool(rules["clinically_reviewed"]),
        )

    level: Level = "self_care"
    primary = next(iter(matched))
    for symptom_id in matched:
        symptom_level: Level = by_id[symptom_id]["level"]
        if _level_index(symptom_level) > _level_index(level):
            level, primary = symptom_level, symptom_id
    reasons.append(f"Highest-priority symptom: {by_id[primary]['label'].lower()} → {rules['levels'][level]['label'].lower()}.")

    # Rule 3: duration.
    if duration_days is None:
        needs_more_info.append("duration")
        reasons.append("How long the symptoms have lasted was not given.")
    else:
        if duration_days >= 21:
            new_level = _at_least(level, "see_doctor_soon")
            if new_level != level:
                reasons.append("Lasting 3 weeks or more → a doctor should check this soon.")
            level = new_level
        elif duration_days > 7:
            new_level = _at_least(level, "routine")
            if new_level != level:
                reasons.append("Lasting more than a week → a doctor should review it.")
            level = new_level

    # Rule 4: severity.
    if severity is None:
        needs_more_info.append("severity")
    elif severity == "severe" and _level_index(level) < _level_index("urgent_same_day"):
        level = LEVEL_ORDER[_level_index(level) + 1]
        reasons.append(f"Described as severe → raised to {rules['levels'][level]['label'].lower()}.")

    # Rule 5: who is affected.
    if age_group == "infant":
        if "fever" in matched or "high_fever" in matched:
            if _level_index(level) < _level_index("urgent_same_day"):
                level = "urgent_same_day"
                reasons.append("Fever in a baby under 1 year should be checked by a doctor today.")
        elif _level_index(level) < _level_index("see_doctor_soon"):
            level = "see_doctor_soon"
            reasons.append("Babies under 1 year should be seen by a doctor soon.")
    if pregnant and ("abdominal_pain" in matched or "vomiting" in matched):
        if _level_index(level) < _level_index("urgent_same_day"):
            level = "urgent_same_day"
            reasons.append("Stomach pain or vomiting during pregnancy should be checked today.")
    if (age_group == "older_adult" or pregnant or care_input.long_term_condition) and level == "self_care":
        level = "routine"
        reasons.append("Older age, pregnancy or a long-term condition → a doctor should review it.")

    # Rule 6: department.
    if level == "urgent_same_day":
        department_id = "emergency"
        reasons.append("Same-day care: the Emergency Department is open 24 hours (appointment requests start tomorrow).")
    else:
        department_id = by_id[primary]["department"]
        if age_group in ("infant", "child") and department_id not in ("emergency",):
            department_id = "paediatrics"
            reasons.append("Child or baby → Paediatrics.")
        elif pregnant and department_id == "general-medicine":
            department_id = "obstetrics-gynaecology"
            reasons.append("Pregnancy → Obstetrics & Gynaecology.")

    support: list[str] = []
    for symptom_id in matched:
        support.extend(number for number in by_id[symptom_id].get("support_numbers", []) if number not in support)

    level_info = rules["levels"][level]
    next_steps = list(level_info["next_steps"])
    if support:
        next_steps.append("Tele-MANAS (14416) offers free, confidential mental-health support 24×7.")
    name, bookable = _department_name(department_id)
    return CareAssessment(
        level=level,
        label=level_info["label"],
        explanation=level_info["explanation"],
        next_steps=next_steps,
        department_id=department_id,
        department_name=name,
        can_request_appointment=bookable and level != "urgent_same_day",
        matched_symptoms=[{"id": sid, "label": by_id[sid]["label"], "matched": phrase} for sid, phrase in matched.items()],
        red_flags=[],
        emergency_numbers=_number_entries(["112", "108"]),
        support_numbers=_number_entries(support),
        reasons=reasons,
        understood=understood,
        needs_more_info=needs_more_info,
        disclaimer=rules["disclaimer"],
        rules_version=rules["version"],
        clinically_reviewed=bool(rules["clinically_reviewed"]),
    )
