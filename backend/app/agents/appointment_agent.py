"""Appointment Agent: books, checks and cancels appointment *requests*.

Booking is a short conversation that fills three details, one at a time:
    department -> preferred date -> reason -> "Shall I submit?" -> saved
The patient's name comes from their signed-in profile.

Honesty rules (also enforced by the shared appointment service):
- A request is saved as "pending". The agent never says it is confirmed.
- Nothing is saved until the patient says yes to the summary card.
- A repeated "yes" cannot create a second request (idempotency key per draft).
"""

import re
import uuid
from datetime import date
from typing import Any

from sqlmodel import select

from app.agents.base import APPOINTMENT, AgentContext, AgentResult, Suggestion
from app.agents.date_parser import parse_preferred_date
from app.agents.department_matcher import match_departments
from app.agents.text import contains_any, find_phrase
from app.core.errors import FieldValidationError
from app.db.models import AppointmentStatus, Department
from app.knowledge import load_care_rules
from app.schemas import AppointmentCreate
from app.services import appointment_service
from app.services.appointment_service import AppointmentConflict, AppointmentNotFound, to_appointment_read

BOOKING_TASK = "appointment_booking"
CANCEL_TASK = "cancel_confirmation"

_REFERENCE = re.compile(r"\bnh-apt-(\d{4})\b")
_YES = ["yes", "y", "yeah", "yep", "yup", "sure", "ok", "okay", "confirm", "submit", "go ahead", "please do", "correct", "haan", "ha"]
_NO = ["no", "nope", "nah", "not now", "don't", "dont", "wait", "change"]
_ABORT = ["stop", "never mind", "nevermind", "forget it", "cancel this", "cancel booking", "cancel the booking", "don't book", "dont book", "no thanks", "exit", "quit", "cancel"]
_REASON_LEAD = re.compile(r"\b(?:because(?: of)?|due to|regarding|reason is|for my|for a|for an)\s+(.+)$", re.IGNORECASE)
_WHITESPACE = re.compile(r"\s+")
_DATE_SUGGESTIONS = [Suggestion("Tomorrow", message="tomorrow"), Suggestion("Next Monday", message="next monday"), Suggestion("In one week", message="in 1 week")]


def _is_yes(text: str) -> bool:
    return bool(contains_any(text, _YES)) and not contains_any(text, ["no", "not", "don't", "dont"])


def _is_no(text: str) -> bool:
    return bool(contains_any(text, _NO))


def _references(text: str) -> list[str]:
    return [f"NH-APT-{digits}" for digits in _REFERENCE.findall(text)]


def _department_chips(ctx: AgentContext) -> list[Suggestion]:
    bookable = ctx.session.exec(
        select(Department).where(Department.accepts_appointments == True).order_by(Department.sort_order)  # noqa: E712
    ).all()
    return [Suggestion(department.name, message=department.name) for department in bookable[:6]]


def _format_date(value: date) -> str:
    return value.strftime("%a, %d %b %Y").replace(" 0", " ")


def _draft_card(ctx: AgentContext, draft: dict[str, Any], *, ready: bool) -> dict[str, Any]:
    department = ctx.session.get(Department, draft["department_id"]) if draft.get("department_id") else None
    preferred = date.fromisoformat(draft["preferred_date"]) if draft.get("preferred_date") else None
    return {
        "type": "appointment_draft",
        "ready": ready,
        "details": {
            "patient_name": ctx.user.full_name,
            "department_id": department.id if department else None,
            "department_name": department.name if department else None,
            "preferred_date": draft.get("preferred_date"),
            "preferred_date_label": _format_date(preferred) if preferred else None,
            "reason": draft.get("reason"),
        },
        "note": "Nothing is saved until you say yes. It will be saved as Pending, not as a confirmed appointment.",
    }


def _clean_reason(raw: str) -> str:
    return _WHITESPACE.sub(" ", raw).strip(" .,!?").capitalize()


# ---------------------------------------------------------------------------
# Booking
# ---------------------------------------------------------------------------
def _fill_slots(ctx: AgentContext, draft: dict[str, Any], *, first_message: bool) -> list[str]:
    """Read any details present in this message. Returns problems to tell the patient."""
    problems: list[str] = []
    awaiting = draft.get("awaiting")
    found: dict[str, Any] = {}

    # Department: fill it when still empty, or when the patient names a different one.
    matches = match_departments(ctx.text)
    named = [m for m in matches if m.kind == "alias"]
    if awaiting != "reason" and (not draft.get("department_id") or named):
        candidates = named or (matches if not draft.get("department_id") else [])
        if len(named) > 1:
            problems.append("You mentioned more than one department. Which one would you like?")
        elif candidates:
            choice = candidates[0]
            department = ctx.session.get(Department, choice.department_id)
            if problem := appointment_service.check_department(department):
                problems.append(problem)
            else:
                draft["department_id"] = choice.department_id
                found["department"] = {"id": choice.department_id, "matched": choice.matched, "kind": choice.kind}
        elif awaiting == "department":
            problems.append("I couldn't match that to a department.")

    # Preferred date.
    if awaiting != "reason" or not draft.get("preferred_date"):
        parsed, matched_text = parse_preferred_date(ctx.text, ctx.today)
        if parsed is not None:
            if problem := appointment_service.check_preferred_date(parsed, ctx.today):
                problems.append(f"{_format_date(parsed)} cannot be used: {problem}")
            else:
                draft["preferred_date"] = parsed.isoformat()
                found["preferred_date"] = {"value": parsed.isoformat(), "matched": matched_text}
        elif awaiting == "date" and not matches:
            problems.append("I couldn't read a date there. You can say “tomorrow”, “next Monday” or a date like 05/11/2026.")

    # Reason: the whole reply when we asked for it, or a "because ..." part of the first message.
    reason: str | None = None
    if awaiting == "reason":
        reason = ctx.message
    elif first_message and (lead := _REASON_LEAD.search(ctx.message)):
        candidate = lead.group(1)
        symptom_phrases = [p for s in load_care_rules()["symptoms"] for p in s["phrases"]]
        if lead.group(0).lower().startswith(("because", "due to", "regarding", "reason")) or contains_any(candidate.lower(), symptom_phrases):
            reason = candidate
    if reason is not None:
        cleaned = _clean_reason(reason)
        if len(cleaned) < 10:
            if awaiting == "reason":
                problems.append("Please describe the reason in at least 10 characters.")
        elif len(cleaned) > 500:
            problems.append("Please keep the reason under 500 characters.")
        else:
            draft["reason"] = cleaned
            found["reason"] = cleaned

    ctx.trace.add(
        APPOINTMENT,
        "extract_details",
        ("Understood: " + ", ".join(f"{key} = {value['matched'] if isinstance(value, dict) else value}" for key, value in found.items()))
        if found
        else "No new booking details found in this message",
        status="warning" if problems else "ok",
        data={"found": found, "problems": problems},
    )
    return problems


def _ask_next(ctx: AgentContext, draft: dict[str, Any], problems: list[str]) -> AgentResult:
    prefix = (" ".join(problems) + " ") if problems else ""

    if not draft.get("department_id"):
        draft["awaiting"] = "department"
        reply = prefix + "Which department would you like the appointment with? If you're not sure, General Medicine is a good place to start."
        chips = _department_chips(ctx)
        summary = "Asked which department to book"
    elif not draft.get("preferred_date"):
        draft["awaiting"] = "date"
        reply = prefix + "What date would you prefer? Requests can be for any day from tomorrow up to 90 days ahead."
        chips = list(_DATE_SUGGESTIONS)
        summary = "Asked for the preferred date"
    elif not draft.get("reason"):
        draft["awaiting"] = "reason"
        reply = prefix + "Briefly, what is the reason for the appointment? (For an emergency, call 112 or 108 instead.)"
        chips = []
        summary = "Asked for the reason"
    else:
        draft["awaiting"] = "confirm"
        reply = prefix + "Here's your request. Shall I submit it? It will be saved as Pending until the hospital reviews it."
        chips = [Suggestion("Yes, submit it", message="yes"), Suggestion("No, don't submit", message="no")]
        summary = "Asked the patient to confirm the request"
        ctx.trace.add(APPOINTMENT, "await_confirmation", "All details collected; waiting for the patient's yes before saving")
        return AgentResult(APPOINTMENT, reply, "needs_input", summary, [_draft_card(ctx, draft, ready=True)], chips, pending_task=BOOKING_TASK, state=draft)

    ctx.trace.add(APPOINTMENT, "ask_for_detail", summary, data={"awaiting": draft["awaiting"]})
    return AgentResult(APPOINTMENT, reply, "needs_input", summary, [_draft_card(ctx, draft, ready=False)], chips, pending_task=BOOKING_TASK, state=draft)


def start_booking(ctx: AgentContext) -> AgentResult:
    draft: dict[str, Any] = {"draft_id": uuid.uuid4().hex[:16], "awaiting": None}
    ctx.trace.add(APPOINTMENT, "start_booking", "Started a new appointment request (name taken from the signed-in profile)")
    problems = _fill_slots(ctx, draft, first_message=True)
    return _ask_next(ctx, draft, problems)


def _submit(ctx: AgentContext, draft: dict[str, Any]) -> AgentResult:
    data = AppointmentCreate(
        patient_name=ctx.user.full_name,
        department_id=draft["department_id"],
        preferred_date=date.fromisoformat(draft["preferred_date"]),
        reason=draft["reason"],
    )
    try:
        result = appointment_service.submit_request(
            ctx.session,
            ctx.user,
            data,
            idempotency_key=f"chat-{draft['draft_id']}",
            source="assistant",
            actor=APPOINTMENT,
            today=ctx.today,
        )
    except FieldValidationError as error:
        # Example: the date stopped being valid while the chat was open.
        for field_name in error.field_errors:
            draft.pop(field_name, None)  # ask for that detail again
        ctx.trace.add(APPOINTMENT, "save_request", "Validation failed: " + "; ".join(error.field_errors.values()), status="warning", data=error.field_errors)
        return _ask_next(ctx, draft, list(error.field_errors.values()))
    except AppointmentConflict as conflict:
        ctx.trace.add(APPOINTMENT, "save_request", str(conflict), status="error")
        return AgentResult(APPOINTMENT, f"I couldn't submit this request: {conflict}", "error", "Submission conflict")

    appointment = to_appointment_read(result.appointment, result.department)
    ctx.trace.add(
        APPOINTMENT,
        "save_request",
        f"Saved {appointment.reference} in the database with status '{appointment.status}'"
        + ("" if result.created else " (same request was already saved; no duplicate created)"),
        data={"reference": appointment.reference, "status": appointment.status, "created": result.created},
    )
    return AgentResult(
        APPOINTMENT,
        f"Done. Your request {appointment.reference} for {appointment.department_name} on "
        f"{_format_date(appointment.preferred_date)} has been saved with the status Pending. "
        "That means it is not yet confirmed: the hospital still needs to review it.",
        "action_completed",
        f"Appointment request {appointment.reference} submitted to {appointment.department_name} (pending)",
        [{"type": "appointment_submitted", "appointment": appointment.model_dump(mode="json")}],
        [Suggestion("View my requests", href="/appointments"), Suggestion("What should I bring?", message="What should I bring to my appointment?")],
        reference=appointment.reference,
        recorded_activity=True,
    )


def continue_booking(ctx: AgentContext) -> AgentResult:
    draft = dict(ctx.state)
    ctx.trace.add(APPOINTMENT, "continue_booking", f"Continuing the unfinished request (waiting for: {draft.get('awaiting') or 'details'})")

    if contains_any(ctx.text, _ABORT) and not _references(ctx.text):
        ctx.trace.add(APPOINTMENT, "abandon_draft", "Patient stopped the booking; nothing was saved")
        return AgentResult(
            APPOINTMENT,
            "Okay, I've stopped. Nothing was submitted. You can start again any time.",
            "answered",
            "Booking stopped by the patient before submitting",
            suggestions=[Suggestion("Book an appointment", message="I want to book an appointment")],
        )

    if draft.get("awaiting") == "confirm":
        if _is_yes(ctx.text):
            return _submit(ctx, draft)
        if _is_no(ctx.text):
            # Let the patient change details instead of losing everything.
            problems = _fill_slots(ctx, draft, first_message=False)
            if problems or ctx.text.strip() in {"no", "nope", "nah", "no thanks"}:
                ctx.trace.add(APPOINTMENT, "abandon_draft", "Patient declined to submit; nothing was saved")
                return AgentResult(
                    APPOINTMENT,
                    "No problem, nothing was submitted. You can start again, or use the appointment form.",
                    "answered",
                    "Patient declined to submit the request",
                    suggestions=[Suggestion("Start again", message="I want to book an appointment"), Suggestion("Open the form", href="/appointments")],
                )
            return _ask_next(ctx, draft, [])
        # They may be changing a detail ("make it Friday instead").
        _fill_slots(ctx, draft, first_message=False)
        return _ask_next(ctx, draft, [])

    problems = _fill_slots(ctx, draft, first_message=False)
    return _ask_next(ctx, draft, problems)


# ---------------------------------------------------------------------------
# Status
# ---------------------------------------------------------------------------
def show_status(ctx: AgentContext) -> AgentResult:
    assert ctx.user.id is not None
    rows = appointment_service.list_requests_for_patient(ctx.session, ctx.user.id)
    wanted = _references(ctx.text)
    if wanted:
        rows = [(a, d) for a, d in rows if a.reference in wanted]
    items = [to_appointment_read(a, d).model_dump(mode="json") for a, d in rows[:5]]
    ctx.trace.add(APPOINTMENT, "lookup_requests", f"Read {len(rows)} of your requests from the database", data={"references": [i["reference"] for i in items]})

    honesty = ""
    if find_phrase(ctx.text, "confirm") or find_phrase(ctx.text, "confirmed"):
        honesty = "Only the hospital can confirm an appointment; I can't change a request's status. "

    if not rows:
        reply = honesty + (f"I couldn't find {', '.join(wanted)} among your requests." if wanted else "You don't have any appointment requests yet.")
        return AgentResult(APPOINTMENT, reply, "answered", "No matching appointment requests", suggestions=[Suggestion("Book an appointment", message="I want to book an appointment")])

    pending = sum(1 for a, _ in rows if a.status == AppointmentStatus.PENDING)
    reply = (
        honesty
        + f"You have {len(rows)} request{'s' if len(rows) != 1 else ''}, {pending} of them pending. "
        "Pending means the hospital has not confirmed it yet; no scheduling system is connected in this prototype."
    )
    return AgentResult(
        APPOINTMENT,
        reply,
        "answered",
        f"Showed {len(items)} appointment request(s) and their real status",
        [{"type": "appointment_list", "items": items}],
        [Suggestion("Open Appointments", href="/appointments")],
    )


# ---------------------------------------------------------------------------
# Cancel
# ---------------------------------------------------------------------------
def _ask_to_cancel(ctx: AgentContext, reference: str) -> AgentResult:
    """Look up one request and ask for a yes before cancelling it."""
    assert ctx.user.id is not None
    try:
        appointment = appointment_service.get_request_for_patient(ctx.session, ctx.user.id, reference)
    except AppointmentNotFound:
        ctx.trace.add(APPOINTMENT, "lookup_request", f"{reference} not found among your requests", status="warning")
        return AgentResult(APPOINTMENT, f"I couldn't find {reference} among your requests.", "answered", "Requested reference not found")
    if appointment.status != AppointmentStatus.PENDING:
        ctx.trace.add(APPOINTMENT, "lookup_request", f"{reference} is {appointment.status}; only pending requests can be cancelled")
        return AgentResult(APPOINTMENT, f"{reference} is already {appointment.status}, so there is nothing to cancel.", "answered", f"{reference} is not pending")
    department = ctx.session.get(Department, appointment.department_id)
    assert department is not None
    ctx.trace.add(APPOINTMENT, "await_confirmation", f"Asking before cancelling {reference}")
    return AgentResult(
        APPOINTMENT,
        f"Do you want me to cancel {reference} ({department.name}, {_format_date(appointment.preferred_date)})? This cannot be undone.",
        "needs_input",
        f"Asked the patient to confirm cancelling {reference}",
        [{"type": "appointment_list", "items": [to_appointment_read(appointment, department).model_dump(mode="json")]}],
        [Suggestion("Yes, cancel it", message="yes"), Suggestion("No, keep it", message="no")],
        pending_task=CANCEL_TASK,
        state={"reference": reference},
    )


def start_cancel(ctx: AgentContext) -> AgentResult:
    assert ctx.user.id is not None
    references = _references(ctx.text)
    if references:
        return _ask_to_cancel(ctx, references[0])

    rows = [(a, d) for a, d in appointment_service.list_requests_for_patient(ctx.session, ctx.user.id) if a.status == AppointmentStatus.PENDING]
    ctx.trace.add(APPOINTMENT, "lookup_requests", f"Found {len(rows)} pending request(s) that could be cancelled")
    if not rows:
        return AgentResult(APPOINTMENT, "You don't have any pending requests to cancel.", "answered", "No pending requests to cancel")
    if len(rows) == 1:
        return _ask_to_cancel(ctx, rows[0][0].reference or "")
    items = [to_appointment_read(a, d).model_dump(mode="json") for a, d in rows[:5]]
    return AgentResult(
        APPOINTMENT,
        "You have more than one pending request. Which one should I cancel?",
        "needs_input",
        "Asked which request to cancel",
        [{"type": "appointment_list", "items": items}],
        [Suggestion(f"Cancel {item['reference']}", message=f"Cancel {item['reference']}") for item in items[:4]],
    )


def continue_cancel(ctx: AgentContext) -> AgentResult:
    reference = ctx.state.get("reference", "")
    if _is_yes(ctx.text):
        try:
            appointment, department = appointment_service.cancel_request(ctx.session, ctx.user, reference, actor=APPOINTMENT)
        except (AppointmentNotFound, AppointmentConflict) as problem:
            ctx.trace.add(APPOINTMENT, "cancel_request", f"Could not cancel {reference}: {problem}", status="warning")
            return AgentResult(APPOINTMENT, f"I couldn't cancel {reference}: {problem}", "answered", f"Cancellation of {reference} not possible")
        ctx.trace.add(APPOINTMENT, "cancel_request", f"Status of {reference} changed to '{appointment.status}' in the database", data={"reference": reference})
        return AgentResult(
            APPOINTMENT,
            f"{reference} has been cancelled.",
            "action_completed",
            f"Appointment request {reference} cancelled",
            [{"type": "appointment_list", "items": [to_appointment_read(appointment, department).model_dump(mode="json")]}],
            [Suggestion("Book a new appointment", message="I want to book an appointment")],
            reference=reference,
            recorded_activity=True,
        )
    ctx.trace.add(APPOINTMENT, "cancel_request", f"Patient chose to keep {reference}")
    return AgentResult(APPOINTMENT, f"Okay, {reference} is unchanged.", "answered", f"Kept {reference}")


def handle(ctx: AgentContext, intent: str) -> AgentResult:
    if intent == "appointment_status":
        return show_status(ctx)
    if intent == "appointment_cancel":
        return start_cancel(ctx)
    return start_booking(ctx)


def continue_task(ctx: AgentContext, task: str) -> AgentResult:
    return continue_cancel(ctx) if task == CANCEL_TASK else continue_booking(ctx)
