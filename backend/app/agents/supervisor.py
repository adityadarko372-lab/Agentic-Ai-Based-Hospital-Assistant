"""Supervisory Agent: receives every assistant message and coordinates the work.

For each message:
 1. Safety Gate      emergency warning signs -> Care Navigation (emergency), always first
                     rule-override / other-people's-data attempts -> refused
 2. Context          an unfinished task (booking, cancel, follow-up) continues
                     unless the patient clearly asks for something else
 3. Intent           IntentClassifier.predict() -> intent, confidence, evidence
 4. Routing          one specialist agent (or a clarifying question if unsure)
 5. Reply + trace    the reply is composed from fixed templates; every step is
                     saved to agent_runs / agent_steps and shown in the UI

The Supervisor has no special powers: it cannot read or change data itself.
Specialists act only through the same services and access checks as the
rest of the app, always on behalf of the signed-in patient.
"""

import json
import secrets
import time
from dataclasses import asdict, dataclass
from typing import Any

from sqlmodel import Session

from app.agents import appointment_agent, care_navigation, health_info_agent, patient_assistance
from app.agents.base import (
    APPOINTMENT,
    CARE_NAVIGATION,
    HEALTH_INFO,
    PATIENT_ASSISTANCE,
    SAFETY_GATE,
    SUPERVISOR,
    AgentContext,
    AgentResult,
    Suggestion,
    Trace,
)
from app.agents.intent import IntentPrediction, get_intent_classifier
from app.agents.safety_gate import check_message
from app.agents.text import normalise
from app.core.clock import today_in_india, utc_now
from app.core.config import get_settings
from app.db.models import AgentRun, AgentStep, Conversation, User
from app.services.activity_service import record_event

# Below this confidence the Supervisor asks instead of guessing.
CONFIDENCE_THRESHOLD = 0.45
# How sure it must be to interrupt an unfinished task with a different request.
SWITCH_THRESHOLD = 0.75

AGENT_FOR_INTENT = {
    "hospital_info": PATIENT_ASSISTANCE,
    "department_query": PATIENT_ASSISTANCE,
    "appointment_book": APPOINTMENT,
    "appointment_status": APPOINTMENT,
    "appointment_cancel": APPOINTMENT,
    "symptom_report": CARE_NAVIGATION,
    "health_info": HEALTH_INFO,
    "greeting": SUPERVISOR,
    "help": SUPERVISOR,
    "out_of_scope": SUPERVISOR,
}
AGENT_FOR_TASK = {
    appointment_agent.BOOKING_TASK: APPOINTMENT,
    appointment_agent.CANCEL_TASK: APPOINTMENT,
    care_navigation.FOLLOWUP_TASK: CARE_NAVIGATION,
}
TASK_LABELS = {
    appointment_agent.BOOKING_TASK: "an unfinished appointment request",
    appointment_agent.CANCEL_TASK: "a cancellation waiting for your yes/no",
    care_navigation.FOLLOWUP_TASK: "a symptom follow-up question",
}

STARTER_SUGGESTIONS = [
    Suggestion("Which department should I visit?", message="Which department should I visit for a consultation?"),
    Suggestion("What should I bring?", message="What should I bring to my appointment?"),
    Suggestion("How do I book?", message="How do I book an appointment?"),
    Suggestion("Hospital services", message="Where can I find hospital services?"),
    Suggestion("Book an appointment", message="I want to book an appointment"),
    Suggestion("I have a mild cough", message="I have had a mild cough for 3 days"),
]


@dataclass
class AssistantTurn:
    conversation_id: str
    run: AgentRun
    steps: list[AgentStep]
    result: AgentResult
    intent: IntentPrediction


class ConversationNotFound(Exception):
    pass


# ---------------------------------------------------------------------------
# Replies the Supervisor gives itself (no specialist needed)
# ---------------------------------------------------------------------------
def _greeting(ctx: AgentContext) -> AgentResult:
    first_name = ctx.user.full_name.split(" ")[0]
    if ctx.text.startswith(("thank", "thx", "ok thanks", "great")):
        reply = "You're welcome. Is there anything else I can help with?"
    elif ctx.text.startswith(("bye", "goodbye", "see you")):
        reply = "Take care. Remember: for an emergency, call 112 or 108."
    else:
        reply = f"Hello {first_name}! I can answer hospital questions, help you request an appointment, or give preliminary guidance on where to seek care."
    return AgentResult(SUPERVISOR, reply, "answered", "Greeted the patient", suggestions=STARTER_SUGGESTIONS[:4])


def _help(_ctx: AgentContext) -> AgentResult:
    items = [
        "Patient Assistance Agent: departments, timings, what to bring, how booking works.",
        "Appointment Agent: request, check or cancel appointment requests (saved as Pending).",
        "Care Navigation Agent: cautious guidance on where and how soon to seek care. It does not diagnose.",
    ]
    if get_settings().health_info_enabled:
        items.append("Health Information Agent: general, cited facts about a condition from NIH MedQuAD. Not advice about you.")
    return AgentResult(
        SUPERVISOR,
        "I'm the Nova Health assistant. I pass your request to the right specialist:",
        "answered",
        "Explained what the assistant can do",
        [{"type": "steps", "title": "Specialist agents", "items": items}],
        STARTER_SUGGESTIONS,
    )


def _out_of_scope(ctx: AgentContext) -> AgentResult:
    medical_advice = any(
        word in ctx.text for word in ("prescri", "medicine", "dose", "dosage", "tablet", "diagnos", "do i have", "is it", "could it be", "is this")
    )
    if medical_advice:
        reply = (
            "I can't diagnose conditions or recommend medicines; only a doctor can do that safely. "
            "I can help you find the right department or request an appointment. If you feel very unwell, call 112 or 108."
        )
        summary = "Declined a diagnosis or medication request; offered navigation instead"
    else:
        reply = "That's outside what I can help with. I'm here for Nova Health hospital services, appointments and care navigation."
        summary = "Declined an out-of-scope request"
    return AgentResult(SUPERVISOR, reply, "refused", summary, suggestions=STARTER_SUGGESTIONS[:4])


def _clarify(_ctx: AgentContext, prediction: IntentPrediction) -> AgentResult:
    return AgentResult(
        SUPERVISOR,
        "I want to make sure I help with the right thing. Could you tell me a bit more, or choose one of these?",
        "clarification",
        f"Asked for clarification (confidence {prediction.confidence:.2f} below {CONFIDENCE_THRESHOLD})",
        suggestions=[
            Suggestion("Find a department", message="Which department should I visit for a consultation?"),
            Suggestion("Book an appointment", message="I want to book an appointment"),
            Suggestion("Check my requests", message="What is the status of my appointment requests?"),
            Suggestion("Get symptom guidance", href="/symptom-guidance"),
        ],
    )


def _refuse_injection(phrases: list[str]) -> AgentResult:
    return AgentResult(
        SUPERVISOR,
        "I can't do that. My safety rules and privacy protections can't be changed from the chat, and I can only show your own "
        "information. Appointment statuses are set by the hospital, not by me. I'm happy to help with hospital services, "
        "your own appointment requests or care navigation.",
        "refused",
        "Refused a request to override rules or access restricted data",
        suggestions=STARTER_SUGGESTIONS[:3],
    )


# ---------------------------------------------------------------------------
# Conversation handling
# ---------------------------------------------------------------------------
def _load_conversation(session: Session, user: User, conversation_id: str | None) -> Conversation:
    if conversation_id:
        conversation = session.get(Conversation, conversation_id)
        # Another patient's conversation is treated as not found.
        if conversation is None or conversation.user_id != user.id:
            raise ConversationNotFound(conversation_id)
        return conversation
    assert user.id is not None
    conversation = Conversation(id=f"conv_{secrets.token_urlsafe(12)}", user_id=user.id)
    session.add(conversation)
    session.flush()
    return conversation


def _route(ctx: AgentContext, prediction: IntentPrediction) -> AgentResult:
    intent = prediction.intent
    if intent in ("hospital_info", "department_query"):
        return patient_assistance.handle(ctx)
    if intent in ("appointment_book", "appointment_status", "appointment_cancel"):
        return appointment_agent.handle(ctx, intent)
    if intent == "symptom_report":
        return care_navigation.handle(ctx)
    if intent == "health_info":
        return health_info_agent.handle(ctx)
    if intent == "greeting":
        return _greeting(ctx)
    if intent == "help":
        return _help(ctx)
    return _out_of_scope(ctx)


def _continue_task(ctx: AgentContext, task: str) -> AgentResult:
    if task in (appointment_agent.BOOKING_TASK, appointment_agent.CANCEL_TASK):
        return appointment_agent.continue_task(ctx, task)
    return care_navigation.continue_followup(ctx)


def handle_message(session: Session, user: User, message: str, conversation_id: str | None = None) -> AssistantTurn:
    started = time.perf_counter()
    trace = Trace()
    conversation = _load_conversation(session, user, conversation_id)
    state: dict[str, Any] = json.loads(conversation.state_json or "{}")
    ctx = AgentContext(session, user, conversation, message, normalise(message), state, trace, today_in_india())
    pending = conversation.pending_task

    trace.add(SUPERVISOR, "receive_message", f"New message ({len(message)} characters) in conversation {conversation.id}")

    # 1. Safety Gate: always first.
    safety = check_message(ctx.text)
    keep_pending = False
    if safety.kind == "emergency":
        trace.add(
            SAFETY_GATE,
            "check_safety",
            "Emergency warning sign(s): " + ", ".join(f"{f.label} (\u201c{f.matched_phrase}\u201d)" for f in safety.red_flags),
            status="warning",
            data={"red_flags": [asdict(f) for f in safety.red_flags], "negated": safety.negated_mentions},
        )
        prediction = IntentPrediction("emergency", 1.0, "safety_rules", [f.matched_phrase for f in safety.red_flags])
        trace.add(SUPERVISOR, "route_request", f"Routed to {CARE_NAVIGATION}: warning signs override every other request", data={"agent": CARE_NAVIGATION})
        result = care_navigation.handle_emergency(ctx, safety)
        if pending:
            trace.add(SUPERVISOR, "update_context", f"Set aside {TASK_LABELS.get(pending, pending)} because of the emergency")
    elif safety.kind == "injection":
        trace.add(SAFETY_GATE, "check_safety", "Blocked: attempt to override rules or reach restricted data", status="blocked", data={"matched": safety.injection_phrases})
        prediction = IntentPrediction("blocked", 1.0, "safety_rules", safety.injection_phrases)
        result = _refuse_injection(safety.injection_phrases)
        keep_pending = True
    else:
        trace.add(
            SAFETY_GATE,
            "check_safety",
            "No emergency warning signs or rule-override attempts"
            + (f" (negated mentions ignored: {', '.join(safety.negated_mentions)})" if safety.negated_mentions else ""),
            data={"negated": safety.negated_mentions},
        )

        # 3. Intent (computed before the context decision, which uses it).
        classifier, fallback_note = get_intent_classifier()
        prediction = classifier.predict(ctx.text)
        if fallback_note:
            trace.add(SUPERVISOR, "select_classifier", fallback_note, status="fallback")
        trace.add(
            SUPERVISOR,
            "classify_intent",
            f"Intent: {prediction.intent} (confidence {prediction.confidence:.2f}, method: {prediction.method})",
            data={"intent": prediction.intent, "confidence": prediction.confidence, "method": prediction.method, "evidence": prediction.evidence, "scores": prediction.scores},
        )

        # 2. Context: continue an unfinished task unless clearly asked something else.
        target_agent = AGENT_FOR_INTENT.get(prediction.intent)
        interrupts = (
            pending is not None
            and prediction.confidence >= SWITCH_THRESHOLD
            and prediction.intent not in ("symptom_report", "department_query", "greeting")
            and (target_agent != AGENT_FOR_TASK.get(pending) or prediction.intent == "appointment_status")
        )
        if pending and not interrupts:
            owner = AGENT_FOR_TASK.get(pending, SUPERVISOR)
            trace.add(SUPERVISOR, "route_request", f"Routed to {owner}: continues {TASK_LABELS.get(pending, pending)}", data={"agent": owner, "task": pending})
            # The routing decision came from the conversation, not from the classifier's
            # guess for a short reply like "yes"; record it that way (the guess stays in the trace).
            prediction = IntentPrediction(
                f"continue_{pending}", 1.0, "conversation_context", [f"unfinished task: {pending}"], prediction.scores
            )
            result = _continue_task(ctx, pending)
        elif prediction.intent == "unknown" or prediction.confidence < CONFIDENCE_THRESHOLD:
            trace.add(SUPERVISOR, "route_request", f"Not confident enough to route (confidence {prediction.confidence:.2f} < {CONFIDENCE_THRESHOLD}); asking the patient", status="warning")
            result = _clarify(ctx, prediction)
            keep_pending = pending is not None
        else:
            agent_name = target_agent or SUPERVISOR
            reason = f"intent {prediction.intent} with confidence {prediction.confidence:.2f} \u2265 {CONFIDENCE_THRESHOLD}"
            if interrupts:
                reason += f"; {TASK_LABELS.get(pending or '', pending)} is kept for later"
                # The interrupting agent must not read the unfinished task's details.
                ctx.state = {}
            trace.add(SUPERVISOR, "route_request", f"Routed to {agent_name}: {reason}", data={"agent": agent_name})
            result = _route(ctx, prediction)
            if interrupts and result.pending_task is None:
                keep_pending = True
                result.reply += f" (You still have {TASK_LABELS.get(pending or '', 'an unfinished task')}; reply to continue it, or say \u201cstop\u201d.)"
                ctx.state = state

    # 5. Compose and record.
    trace.add(SUPERVISOR, "compose_reply", "Reply built from fixed templates (optional AI phrasing is off)")
    if keep_pending and result.pending_task is None:
        conversation.pending_task, conversation.state_json = pending, json.dumps(state)
    else:
        conversation.pending_task = result.pending_task
        conversation.state_json = json.dumps(result.state if result.pending_task else {})
    conversation.updated_at = utc_now()

    trace.add(SUPERVISOR, "record_outcome", f"Outcome: {result.outcome_status}. {result.outcome_summary}", status="warning" if result.outcome_status in ("emergency_escalation", "refused") else "ok")

    run = AgentRun(
        conversation_id=conversation.id,
        user_id=user.id or 0,
        user_message=message[:1000],
        detected_intent=prediction.intent,
        confidence=prediction.confidence,
        classifier_method=prediction.method,
        selected_agent=result.agent,
        outcome_status=result.outcome_status,
        outcome_summary=result.outcome_summary[:300],
        reference=result.reference,
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

    # A readable history line, unless the agent already wrote one (e.g. "request submitted").
    if not result.recorded_activity:
        record_event(
            session,
            user_id=user.id or 0,
            event_type=f"assistant.{result.outcome_status}",
            actor=result.agent,
            summary=result.outcome_summary[:200],
            reference=result.reference,
        )
    session.commit()
    session.refresh(run)
    return AssistantTurn(conversation.id, run, steps, result, prediction)
