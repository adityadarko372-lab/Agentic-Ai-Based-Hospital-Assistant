"""SQLite tables (SQLModel).

Phase 2 tables:
- users                 demo accounts (patients)
- departments           fictional hospital directory, seeded from hospital_info.json
- appointment_requests  requests submitted by patients; always start as "pending"
- activity_events       a readable history of what happened and who did it

Phase 3 tables (the multi-agent system):
- conversations         one assistant chat; remembers an unfinished task (e.g. a booking draft)
- agent_runs            one row per message: intent, chosen agent, outcome
- agent_steps           the ordered steps inside a run (safety check, routing, actions)
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


# ---------------------------------------------------------------------------
# Phase 3: multi-agent conversation and trace
# ---------------------------------------------------------------------------


class Conversation(SQLModel, table=True):
    __tablename__ = "conversations"

    # Random id handed to the browser (not guessable, not sequential).
    id: str = Field(primary_key=True, max_length=40)
    user_id: int = Field(foreign_key="users.id", index=True)
    # An unfinished task that the next message may continue, e.g.
    # "appointment_booking", "cancel_confirmation", "care_followup".
    pending_task: str | None = Field(default=None, max_length=40)
    # JSON with the task's collected details (e.g. department and date so far).
    state_json: str = Field(default="{}")
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class AgentRun(SQLModel, table=True):
    """One user message handled by the Supervisory Agent."""

    __tablename__ = "agent_runs"

    id: int | None = Field(default=None, primary_key=True)
    conversation_id: str = Field(foreign_key="conversations.id", index=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    # The patient's own words, shown only to that patient in their history.
    user_message: str = Field(max_length=1000)
    detected_intent: str = Field(max_length=40)
    confidence: float
    classifier_method: str = Field(max_length=40)
    selected_agent: str = Field(max_length=60)
    # answered | needs_input | action_completed | emergency_escalation |
    # refused | clarification | information_unavailable | error
    outcome_status: str = Field(max_length=40)
    outcome_summary: str = Field(max_length=300)
    reference: str | None = Field(default=None, max_length=20)
    duration_ms: int = 0
    created_at: datetime = Field(default_factory=utc_now, index=True)


class AgentStep(SQLModel, table=True):
    """One visible step inside a run, in order."""

    __tablename__ = "agent_steps"

    id: int | None = Field(default=None, primary_key=True)
    run_id: int = Field(foreign_key="agent_runs.id", index=True)
    step_order: int
    agent: str = Field(max_length=60)
    action: str = Field(max_length=60)
    # ok | warning | blocked | fallback | error
    status: str = Field(max_length=20)
    detail: str = Field(max_length=500)
    # JSON with structured evidence (matched words, scores, references).
    data_json: str = Field(default="{}")
    duration_ms: int = 0
