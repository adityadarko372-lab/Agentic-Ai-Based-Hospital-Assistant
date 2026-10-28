"""Care Navigation Agent: cautious, preliminary guidance on where and how soon
to seek care. It uses the shared care engine (fixed rules, not clinically
reviewed) and never names a condition or suggests a medicine.

- Warning signs: answered immediately with emergency guidance (no questions first).
- Otherwise: if how long / how bad is unknown, it asks ONE short follow-up,
  then gives guidance, a suggested department and the next steps.
"""

from dataclasses import asdict

from app.agents.base import CARE_NAVIGATION, AgentContext, AgentResult, Suggestion, Trace
from app.agents.care_engine import CareAssessment, CareInput, evaluate
from app.agents.safety_gate import SafetyResult

FOLLOWUP_TASK = "care_followup"


def _guidance_card(assessment: CareAssessment) -> dict:
    return {"type": "care_guidance", "assessment": asdict(assessment)}


def _trace_assessment(ctx: AgentContext, assessment: CareAssessment) -> None:
    trace_assessment(ctx.trace, assessment)


def trace_assessment(trace: Trace, assessment: CareAssessment) -> None:
    """Shared by the chat and the Symptom Guidance form, so both traces look the same."""
    trace.add(
        CARE_NAVIGATION,
        "apply_care_rules",
        f"Level: {assessment.label}"
        + (f"; department: {assessment.department_name}" if assessment.department_name else "")
        + f" (rules v{assessment.rules_version}, not clinically reviewed)",
        status="warning" if assessment.level in ("emergency", "urgent_same_day") else "ok",
        data={
            "level": assessment.level,
            "reasons": assessment.reasons,
            "symptoms": assessment.matched_symptoms,
            "understood": assessment.understood,
        },
    )


def _result_for(ctx: AgentContext, assessment: CareAssessment) -> AgentResult:
    suggestions: list[Suggestion] = []
    if assessment.can_request_appointment and assessment.department_id:
        suggestions.append(Suggestion(f"Request {assessment.department_name}", href=f"/appointments?department={assessment.department_id}"))
        suggestions.append(Suggestion("Book it here", message=f"I want to book an appointment with {assessment.department_name}"))
    suggestions.append(Suggestion("Use the symptom form", href="/symptom-guidance"))

    if assessment.level is None:
        reply = "I couldn't recognise the symptoms from that. Could you describe the main symptom in simple words?"
        status = "needs_input"
    elif assessment.level == "urgent_same_day":
        reply = f"{assessment.label}. {assessment.explanation} This is not a diagnosis."
        status = "answered"
    else:
        reply = (
            f"{assessment.label}. {assessment.explanation}"
            + (f" Suggested department: {assessment.department_name}." if assessment.department_name else "")
            + " This is preliminary guidance from fixed rules, not a diagnosis."
        )
        status = "answered"
    return AgentResult(
        CARE_NAVIGATION,
        reply,
        status,  # type: ignore[arg-type]
        f"Preliminary guidance: {assessment.label}"
        + (f" ({assessment.department_name})" if assessment.department_name and assessment.level else ""),
        [_guidance_card(assessment)],
        suggestions,
        [f"Nova Health care-navigation rules v{assessment.rules_version} (not clinically reviewed)"],
    )


def handle_emergency(ctx: AgentContext, safety: SafetyResult) -> AgentResult:
    """Warning signs found by the Safety Gate: emergency guidance straight away."""
    assessment = evaluate(CareInput(text=ctx.message))
    if assessment.level != "emergency":
        # Defensive: the gate and the engine share the same rules, so this should not happen.
        ctx.trace.add(CARE_NAVIGATION, "apply_care_rules", "Engine disagreed with the Safety Gate; emergency guidance kept", status="warning")
    _trace_assessment(ctx, assessment)
    numbers = safety.emergency_numbers
    signs = ", ".join(flag.label.lower() for flag in safety.red_flags)
    is_self_harm = any(flag.id == "self_harm" for flag in safety.red_flags)
    if is_self_harm:
        reply = (
            "I'm really sorry you're going through this. Your safety matters most right now. "
            "If you are in immediate danger, call 112. You can also call Tele-MANAS on 14416, free and available 24×7, "
            "to talk to a trained counsellor. If you can, reach out to someone you trust and stay with them."
        )
    else:
        reply = (
            f"This could be an emergency ({signs}). Please call 112 or 108 now, or go to the nearest emergency department. "
            "Do not wait for an appointment, and do not drive yourself if you can avoid it."
        )
    return AgentResult(
        CARE_NAVIGATION,
        reply,
        "emergency_escalation",
        f"Emergency guidance shown for: {signs}",
        [{"type": "emergency", "red_flags": [flag.label for flag in safety.red_flags], "numbers": numbers, "next_steps": assessment.next_steps, "self_harm": is_self_harm}],
        [Suggestion("Emergency Department details", message="Where is the emergency department?")],
        [f"Nova Health care-navigation rules v{assessment.rules_version} (not clinically reviewed)"],
    )


def handle(ctx: AgentContext) -> AgentResult:
    assessment = evaluate(CareInput(text=ctx.message))
    _trace_assessment(ctx, assessment)

    # One focused follow-up when the answer depends on how long / how bad.
    missing = [item for item in assessment.needs_more_info if item in ("duration", "severity")]
    if assessment.level in ("self_care", "routine", "see_doctor_soon") and missing:
        questions = []
        if "duration" in missing:
            questions.append("how long you've had this")
        if "severity" in missing:
            questions.append("whether it is mild, moderate or severe")
        ctx.trace.add(CARE_NAVIGATION, "ask_followup", "Asked one follow-up question: " + " and ".join(questions))
        return AgentResult(
            CARE_NAVIGATION,
            f"Thanks for telling me. To guide you, could you tell me {' and '.join(questions)}? "
            "If anything feels seriously wrong, call 112 or 108 now.",
            "needs_input",
            "Asked how long and how severe the symptoms are",
            [],
            [Suggestion("Since yesterday, mild", message="Since yesterday, it's mild"), Suggestion("3 days, moderate", message="For 3 days, moderate"), Suggestion("Over a week, severe", message="For over 2 weeks, severe")],
            pending_task=FOLLOWUP_TASK,
            state={"text": ctx.message},
        )
    return _result_for(ctx, assessment)


def continue_followup(ctx: AgentContext) -> AgentResult:
    """Combine the first description with the follow-up answer, then give guidance."""
    combined = f"{ctx.state.get('text', '')}. {ctx.message}"
    ctx.trace.add(CARE_NAVIGATION, "combine_answers", "Combined the original description with the follow-up answer")
    assessment = evaluate(CareInput(text=combined))
    _trace_assessment(ctx, assessment)
    return _result_for(ctx, assessment)
