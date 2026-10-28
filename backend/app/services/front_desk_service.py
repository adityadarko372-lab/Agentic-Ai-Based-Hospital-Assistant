"""Front-desk review of appointment requests (Phase 5, optional).

This is the human-in-the-loop step from Context.md section 10: a request only
becomes "confirmed" or "declined" when a signed-in front-desk staff member
decides. No agent and no patient can do this.

Rules:
- Only a PENDING request can be decided, and only once. The decision is a
  single conditional UPDATE ("... WHERE status = 'pending'"), so two staff
  clicking at the same moment cannot both succeed.
- Declining needs a short note so the patient knows why.
- The patient gets an activity event; the staff note is shown on the request.
"""

from typing import Literal

from sqlalchemy import update
from sqlmodel import Session, col, select

from app.core.clock import utc_now
from app.core.errors import FieldValidationError
from app.db.models import AppointmentRequest, AppointmentStatus, Department, User
from app.services.activity_service import record_event
from app.services.appointment_service import AppointmentConflict, AppointmentNotFound

FRONT_DESK_ACTOR = "Front Desk"


def list_requests(session: Session, status: str | None = "pending") -> list[tuple[AppointmentRequest, Department, User]]:
    statement = (
        select(AppointmentRequest, Department, User)
        .join(Department, col(Department.id) == col(AppointmentRequest.department_id))
        .join(User, col(User.id) == col(AppointmentRequest.patient_id))
    )
    if status:
        statement = statement.where(AppointmentRequest.status == AppointmentStatus(status))
    # Pending: earliest preferred date first (most urgent to review). Others: most recently reviewed first.
    if status == "pending":
        statement = statement.order_by(col(AppointmentRequest.preferred_date), col(AppointmentRequest.id))
    else:
        statement = statement.order_by(col(AppointmentRequest.updated_at).desc())
    return list(session.exec(statement.limit(200)))


def decide(
    session: Session, staff: User, reference: str, decision: Literal["confirm", "decline"], note: str
) -> tuple[AppointmentRequest, Department, User]:
    appointment = session.exec(select(AppointmentRequest).where(AppointmentRequest.reference == reference.upper())).first()
    if appointment is None:
        raise AppointmentNotFound(reference)
    if decision == "decline" and len(note) < 3:
        raise FieldValidationError({"note": "Please add a short note for the patient explaining why."})

    new_status = AppointmentStatus.CONFIRMED if decision == "confirm" else AppointmentStatus.DECLINED
    now = utc_now()
    result = session.exec(  # type: ignore[call-overload]
        update(AppointmentRequest)
        .where(col(AppointmentRequest.id) == appointment.id, col(AppointmentRequest.status) == AppointmentStatus.PENDING)
        .values(status=new_status, reviewed_by=staff.full_name, reviewed_at=now, review_note=note or None, updated_at=now)
    )
    if result.rowcount != 1:
        session.rollback()
        session.refresh(appointment)
        raise AppointmentConflict(f"{appointment.reference} is already {appointment.status}; it can only be decided once.")

    department = session.get(Department, appointment.department_id)
    patient = session.get(User, appointment.patient_id)
    assert department is not None and patient is not None
    verb = "confirmed" if decision == "confirm" else "declined"
    record_event(
        session,
        user_id=patient.id or 0,
        event_type=f"appointment.{verb}",
        actor=FRONT_DESK_ACTOR,
        summary=f"Appointment request to {department.name} was {verb} by the hospital front desk.",
        reference=appointment.reference,
    )
    session.commit()
    session.refresh(appointment)
    return appointment, department, patient
