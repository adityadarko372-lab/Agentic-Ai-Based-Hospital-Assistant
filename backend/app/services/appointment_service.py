"""Appointment request rules (Module 5).

This is the single place where appointment requests are created, so the
form (Phase 2) and the Appointment Agent (Phase 3) follow identical rules.

Honesty rule: a request is always created with status "pending". Nothing in
this service can mark a request as confirmed; that requires a hospital-side
review that this prototype does not perform.
"""

from dataclasses import dataclass
from datetime import date, timedelta

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, col, select

from app.core.clock import today_in_india, utc_now
from app.core.config import get_settings
from app.core.errors import FieldValidationError
from app.db.models import AppointmentRequest, AppointmentStatus, Department, User
from app.schemas import AppointmentCreate
from app.services.activity_service import record_event


class AppointmentNotFound(Exception):
    """The request does not exist or belongs to another patient."""


class AppointmentConflict(Exception):
    """The requested change is not allowed in the request's current state."""


@dataclass
class SubmissionResult:
    appointment: AppointmentRequest
    department: Department
    # False when an identical earlier submission was returned (idempotent replay).
    created: bool


def format_reference(appointment_id: int) -> str:
    return f"NH-APT-{appointment_id:04d}"


def validate_business_rules(session: Session, data: AppointmentCreate, today: date | None = None) -> Department:
    """Checks that need the database or today's date. Raises FieldValidationError."""
    today = today or today_in_india()
    max_days = get_settings().appointment_max_days_ahead
    errors: dict[str, str] = {}

    department = session.get(Department, data.department_id)
    if department is None:
        errors["department_id"] = "Please choose a department from the list."
    elif not department.accepts_appointments:
        errors["department_id"] = (
            f"{department.name} does not take appointment requests. {department.summary}"
        )

    if data.preferred_date <= today:
        errors["preferred_date"] = "Please choose a date from tomorrow onwards."
    elif data.preferred_date > today + timedelta(days=max_days):
        errors["preferred_date"] = f"Please choose a date within the next {max_days} days."

    if errors:
        raise FieldValidationError(errors)
    assert department is not None
    return department


def _same_details(existing: AppointmentRequest, data: AppointmentCreate) -> bool:
    return (
        existing.patient_name == data.patient_name
        and existing.department_id == data.department_id
        and existing.preferred_date == data.preferred_date
        and existing.reason == data.reason
    )


def _find_by_key(session: Session, patient_id: int, idempotency_key: str) -> AppointmentRequest | None:
    return session.exec(
        select(AppointmentRequest).where(
            AppointmentRequest.patient_id == patient_id,
            AppointmentRequest.idempotency_key == idempotency_key,
        )
    ).first()


def submit_request(
    session: Session,
    patient: User,
    data: AppointmentCreate,
    idempotency_key: str,
    *,
    source: str = "form",
    actor: str = "You",
    today: date | None = None,
) -> SubmissionResult:
    """Validate and save a new request as Pending, plus an activity event.

    Repeating the call with the same idempotency key returns the original
    request instead of creating a duplicate.
    """
    assert patient.id is not None

    existing = _find_by_key(session, patient.id, idempotency_key)
    if existing is not None:
        if not _same_details(existing, data):
            raise AppointmentConflict("This submission was already used for a different request. Please reload the form.")
        department = session.get(Department, existing.department_id)
        assert department is not None
        return SubmissionResult(existing, department, created=False)

    department = validate_business_rules(session, data, today)

    appointment = AppointmentRequest(
        patient_id=patient.id,
        patient_name=data.patient_name,
        department_id=department.id,
        preferred_date=data.preferred_date,
        reason=data.reason,
        status=AppointmentStatus.PENDING,
        source=source,
        idempotency_key=idempotency_key,
    )
    session.add(appointment)
    try:
        session.flush()  # assigns appointment.id
        assert appointment.id is not None
        appointment.reference = format_reference(appointment.id)
        record_event(
            session,
            user_id=patient.id,
            event_type="appointment.submitted",
            actor=actor,
            summary=f"Appointment request submitted to {department.name}. Status: pending hospital review.",
            reference=appointment.reference,
        )
        session.commit()
    except IntegrityError:
        # Two identical submissions raced; the other one won. Return it.
        session.rollback()
        winner = _find_by_key(session, patient.id, idempotency_key)
        if winner is None:
            raise
        return SubmissionResult(winner, department, created=False)

    session.refresh(appointment)
    return SubmissionResult(appointment, department, created=True)


def list_requests_for_patient(session: Session, patient_id: int) -> list[tuple[AppointmentRequest, Department]]:
    statement = (
        select(AppointmentRequest, Department)
        .join(Department, col(Department.id) == col(AppointmentRequest.department_id))
        .where(AppointmentRequest.patient_id == patient_id)
        .order_by(col(AppointmentRequest.created_at).desc(), col(AppointmentRequest.id).desc())
    )
    return list(session.exec(statement))


def get_request_for_patient(session: Session, patient_id: int, reference: str) -> AppointmentRequest:
    appointment = session.exec(
        select(AppointmentRequest).where(AppointmentRequest.reference == reference.upper())
    ).first()
    # Another patient's request is reported as "not found" so its existence is not revealed.
    if appointment is None or appointment.patient_id != patient_id:
        raise AppointmentNotFound(reference)
    return appointment


def cancel_request(
    session: Session, patient: User, reference: str, *, actor: str = "You"
) -> tuple[AppointmentRequest, Department]:
    """Withdraw a pending request. Only the owner can do this."""
    assert patient.id is not None
    appointment = get_request_for_patient(session, patient.id, reference)
    if appointment.status != AppointmentStatus.PENDING:
        raise AppointmentConflict(f"Request {appointment.reference} is already {appointment.status} and cannot be cancelled.")

    department = session.get(Department, appointment.department_id)
    assert department is not None
    appointment.status = AppointmentStatus.CANCELLED
    appointment.updated_at = utc_now()
    record_event(
        session,
        user_id=patient.id,
        event_type="appointment.cancelled",
        actor=actor,
        summary=f"Appointment request to {department.name} was cancelled.",
        reference=appointment.reference,
    )
    session.commit()
    session.refresh(appointment)
    return appointment, department
