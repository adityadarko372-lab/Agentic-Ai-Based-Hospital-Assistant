"""SQLite tables (SQLModel).

Phase 2 tables:
- users                 demo accounts (patients)
- departments           fictional hospital directory, seeded from hospital_info.json
- appointment_requests  requests submitted by patients; always start as "pending"
- activity_events       a readable history of what happened and who did it

The agent trace tables (agent_runs / agent_steps) are added in Phase 3, when
the Supervisory Agent actually writes to them.
"""

from datetime import date, datetime
from enum import StrEnum

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel

from app.core.clock import utc_now


class UserRole(StrEnum):
    PATIENT = "patient"


class AppointmentStatus(StrEnum):
    # Submitted by the patient, not yet reviewed by hospital staff.
    PENDING = "pending"
    # Withdrawn by the patient before any hospital decision.
    CANCELLED = "cancelled"
    # "confirmed" / "declined" are reserved for a staff review workflow
    # (optional Phase 5). Nothing in Phase 2 can set them.


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: int | None = Field(default=None, primary_key=True)
    email: str = Field(index=True, unique=True, max_length=254)
    full_name: str = Field(max_length=80)
    password_hash: str
    role: UserRole = Field(default=UserRole.PATIENT)
    created_at: datetime = Field(default_factory=utc_now)


class Department(SQLModel, table=True):
    __tablename__ = "departments"

    # Stable slug such as "general-medicine", used in URLs and forms.
    id: str = Field(primary_key=True, max_length=60)
    name: str = Field(max_length=80)
    category: str = Field(max_length=20)  # "clinical" or "service"
    summary: str
    location: str
    opening_hours: str
    extension: str
    accepts_appointments: bool = True
    icon: str = "stethoscope"
    sort_order: int = 0


class AppointmentRequest(SQLModel, table=True):
    __tablename__ = "appointment_requests"
    # One idempotency key per patient: a repeated submission with the same key
    # (double-click, network retry) returns the original request instead of
    # creating a duplicate.
    __table_args__ = (UniqueConstraint("patient_id", "idempotency_key", name="uq_patient_idempotency"),)

    id: int | None = Field(default=None, primary_key=True)
    # Human-readable reference, e.g. NH-APT-0007. Set right after insert.
    reference: str | None = Field(default=None, index=True, unique=True, max_length=20)
    patient_id: int = Field(foreign_key="users.id", index=True)
    patient_name: str = Field(max_length=80)
    department_id: str = Field(foreign_key="departments.id")
    preferred_date: date
    reason: str = Field(max_length=500)
    status: AppointmentStatus = Field(default=AppointmentStatus.PENDING)
    # Where the request came from: the form (Phase 2) or the assistant (Phase 3).
    source: str = Field(default="form", max_length=20)
    idempotency_key: str = Field(max_length=80)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class ActivityEvent(SQLModel, table=True):
    __tablename__ = "activity_events"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    # Machine-readable type, e.g. "appointment.submitted".
    event_type: str = Field(max_length=60)
    # Who performed the action: "You" for the patient, or an agent name later.
    actor: str = Field(max_length=60)
    # Short plain-language description. Avoids copying free-text medical
    # details (such as the appointment reason) into the history.
    summary: str = Field(max_length=200)
    reference: str | None = Field(default=None, max_length=20)
    created_at: datetime = Field(default_factory=utc_now, index=True)
