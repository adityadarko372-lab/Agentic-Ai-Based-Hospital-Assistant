"""Symptom Guidance form (Module 4).

The form is handled by the Care Navigation Agent using the SAME care engine
as the chat, so the same answers always give the same guidance. Every form
submission is saved as an agent run with its steps, like a chat message, so
it appears in the Agent Activity history.
"""

import json
import secrets
import time
from dataclasses import asdict
from typing import Any

from sqlmodel import Session

from app.agents.base import CARE_NAVIGATION, SAFETY_GATE, Trace
from app.agents.care_engine import CareAssessment, CareInput, evaluate
from app.agents.care_navigation import trace_assessment
from app.core.errors import FieldValidationError
from app.db.models import AgentRun, AgentStep, Conversation, User
from app.knowledge import load_care_rules
from app.schemas import CareAssessRequest
from app.services.activity_service import record_event

# Each answer maps to a representative number of days used by the rules
# (">7 days" and ">=21 days" are the thresholds that matter).
DURATION_OPTIONS: list[dict[str, Any]] = [
    {"id": "under_1_day", "label": "Less than a day", "days": 0.5},
    {"id": "1_3_days", "label": "1 to 3 days", "days": 2},
    {"id": "4_7_days", "label": "4 to 7 days", "days": 5},
    {"id": "1_3_weeks", "label": "1 to 3 weeks", "days": 14},
    {"id": "over_3_weeks", "label": "More than 3 weeks", "days": 30},
]
DURATION_DAYS = {option["id"]: option["days"] for option in DURATION_OPTIONS}
DURATION_LABELS = {option["id"]: option["label"] for option in DURATION_OPTIONS}

SEVERITY_OPTIONS = [
    {"id": "mild", "label": "Mild", "hint": "Noticeable, but daily activities are normal"},
    {"id": "moderate", "label": "Moderate", "hint": "It gets in the way of some activities"},
    {"id": "severe", "label": "Severe", "hint": "Very hard to bear or to carry on as usual"},
]
AGE_GROUP_OPTIONS = [
    {"id": "infant", "label": "Baby (under 1 year)"},
    {"id": "child", "label": "Child (1–15 years)"},
    {"id": "adult", "label": "Adult (16–64 years)"},
    {"id": "older_adult", "label": "Older adult (65+ years)"},
]
# Too vague to be useful as a tick box; still recognised in free text.
_HIDDEN_SYMPTOMS = {"general_pain"}


def form_options() -> dict[str, Any]:
    rules = load_care_rules()
    return {
        "warning_signs": [{"id": rule["id"], "label": rule["label"]} for rule in rules["red_flags"]],
        "symptoms": [
            {"id": symptom["id"], "label": symptom["label"]}
            for symptom in rules["symptoms"]
            if symptom["id"] not in _HIDDEN_SYMPTOMS
        ],
        "durations": [{"id": o["id"], "label": o["label"]} for o in DURATION_OPTIONS],
        "severities": SEVERITY_OPTIONS,
        "age_groups": AGE_GROUP_OPTIONS,
        "emergency_numbers": [{"number": n, "label": label} for n, label in rules["emergency_numbers"].items()],
        "disclaimer": rules["disclaimer"],
        "rules_version": rules["version"],
        "clinically_reviewed": bool(rules["clinically_reviewed"]),
    }


def _labels() -> dict[str, str]:
    rules = load_care_rules()
    return {item["id"]: item["label"] for item in [*rules["red_flags"], *rules["symptoms"]]}


def validate(data: CareAssessRequest) -> None:
    known = _labels()
    errors: dict[str, str] = {}
    unknown = [symptom_id for symptom_id in data.symptom_ids if symptom_id not in known]
    if unknown:
        errors["symptom_ids"] = "Please choose symptoms from the list."
    elif not data.symptom_ids and len(data.free_text) < 3:
        errors["symptom_ids"] = "Please select at least one symptom or describe how you feel."
    if errors:
        raise FieldValidationError(errors)


def _form_summary(data: CareAssessRequest) -> str:
    labels = _labels()
    parts = [", ".join(labels[s] for s in data.symptom_ids)] if data.symptom_ids else []
    if data.free_text:
        parts.append(f"“{data.free_text[:150]}”")
    if data.duration:
        parts.append(DURATION_LABELS[data.duration].lower())
    if data.severity:
        parts.append(data.severity)
    return ("Symptom form: " + " · ".join(parts))[:1000]


def assess(session: Session, user: User, data: CareAssessRequest) -> tuple[CareAssessment, AgentRun, list[AgentStep]]:
    """Evaluate the form with the shared care engine and save the trace."""
    validate(data)
    started = time.perf_counter()
    trace = Trace()

    trace.add(
        CARE_NAVIGATION,
        "receive_form",
        f"Symptom form received: {len(data.symptom_ids)} item(s) ticked"
        + (", own description given" if data.free_text else "")
        + (f", duration {DURATION_LABELS[data.duration].lower()}" if data.duration else "")
        + (f", severity {data.severity}" if data.severity else ""),
        data={"symptom_ids": data.symptom_ids, "duration": data.duration, "severity": data.severity, "age_group": data.age_group},
    )

    care_input = CareInput(
        text=data.free_text,
        symptom_ids=list(data.symptom_ids),
        duration_days=DURATION_DAYS[data.duration] if data.duration else None,
        severity=data.severity,
        age_group=data.age_group,
        pregnant=True if data.pregnant else None,
        long_term_condition=data.long_term_condition,
    )
    assessment = evaluate(care_input)

    if assessment.red_flags:
        trace.add(
            SAFETY_GATE,
            "check_safety",
            "Emergency warning sign(s): " + ", ".join(f"{flag['label']} ({flag['matched']})" for flag in assessment.red_flags),
            status="warning",
            data={"red_flags": assessment.red_flags},
        )
    else:
        trace.add(SAFETY_GATE, "check_safety", "No emergency warning signs ticked or described")
    trace_assessment(trace, assessment)

    if assessment.level == "emergency":
        outcome_status, summary = "emergency_escalation", "Emergency guidance shown for: " + ", ".join(
            flag["label"].lower() for flag in assessment.red_flags
        )
    elif assessment.level is None:
        outcome_status, summary = "needs_input", "Symptoms not recognised; asked for more detail"
    else:
        outcome_status = "answered"
        summary = f"Preliminary guidance: {assessment.label}" + (
            f" ({assessment.department_name})" if assessment.department_name else ""
        )
    trace.add(
        CARE_NAVIGATION,
        "record_outcome",
        f"Outcome: {outcome_status}. {summary}",
        status="warning" if outcome_status == "emergency_escalation" else "ok",
    )

    # Each form submission gets its own conversation record so it can be traced like a chat run.
    assert user.id is not None
    conversation = Conversation(id=f"form_{secrets.token_urlsafe(12)}", user_id=user.id)
    session.add(conversation)
    session.flush()
    run = AgentRun(
        conversation_id=conversation.id,
        user_id=user.id,
        user_message=_form_summary(data),
        detected_intent="symptom_form",
        confidence=1.0,
        classifier_method="form",  # the patient chose the Symptom Guidance module directly
        selected_agent=CARE_NAVIGATION,
        outcome_status=outcome_status,
        outcome_summary=summary[:300],
        duration_ms=int((time.perf_counter() - started) * 1000),
    )
    session.add(run)
    session.flush()
    assert run.id is not None
    steps = [
        AgentStep(
            run_id=run.id,
            step_order=index,
            agent=step.agent,
            action=step.action,
            status=step.status,
            detail=step.detail,
            data_json=json.dumps(step.data, default=str),
            duration_ms=step.duration_ms,
        )
        for index, step in enumerate(trace.steps, start=1)
    ]
    session.add_all(steps)
    # The history line uses fixed wording only; the patient's own description is not copied.
    record_event(session, user_id=user.id, event_type="care.assessment", actor=CARE_NAVIGATION, summary=summary[:200])
    session.commit()
    session.refresh(run)
    return assessment, run, steps


def assessment_to_dict(assessment: CareAssessment) -> dict[str, Any]:
    return asdict(assessment)
