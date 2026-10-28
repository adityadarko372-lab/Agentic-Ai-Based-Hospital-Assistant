"""Request and response shapes for the HTTP API.

Validators return short, friendly messages because they are shown directly
to patients next to the form field (see app/core/errors.py).
"""

import re
import unicodedata
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

_WHITESPACE = re.compile(r"\s+")
# Shape of a valid name once every word is reduced to "a":
#   a word, then any number of (". " | "." | " " | "'" | "-") + word, optional final "."
# Examples: "Asha Verma", "Dr. K. Iyer", "Anne-Marie D'Souza", "आशा वर्मा".
# The same rule is used by the frontend (appointmentValidation.ts).
_NAME_SHAPE = re.compile(r"^a(?:(?:\. ?|[ '-])a)*\.?$")


def _is_valid_name(value: str) -> bool:
    """Letters and combining marks, separated by space . ' -

    Combining marks (Unicode category M) are needed for Indian scripts:
    the vowel signs in "आशा" are marks, not letters. A word must start with
    a letter, so digits, underscores and symbols are rejected.
    """
    shape: list[str] = []
    for char in value:
        category = unicodedata.category(char)
        if category.startswith("L"):
            if not shape or shape[-1] != "a":
                shape.append("a")
        elif category.startswith("M"):
            if not shape or shape[-1] != "a":
                return False  # a mark cannot start a word
        else:
            shape.append(char)
    return bool(_NAME_SHAPE.match("".join(shape)))


# ---------- Auth ----------
class LoginRequest(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(max_length=128)

    @field_validator("email")
    @classmethod
    def normalise_email(cls, value: str) -> str:
        value = value.strip().lower()
        if not value or "@" not in value:
            raise ValueError("Please enter your email address.")
        return value

    @field_validator("password")
    @classmethod
    def password_required(cls, value: str) -> str:
        if not value:
            raise ValueError("Please enter your password.")
        return value


class UserRead(BaseModel):
    id: int
    email: str
    full_name: str
    role: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: datetime
    user: UserRead


# ---------- Hospital directory ----------
class DepartmentRead(BaseModel):
    id: str
    name: str
    category: str
    summary: str
    location: str
    opening_hours: str
    extension: str
    accepts_appointments: bool
    icon: str


# ---------- Appointments ----------
class AppointmentCreate(BaseModel):
    patient_name: str = Field(max_length=200)
    department_id: str = Field(max_length=60)
    preferred_date: date
    reason: str = Field(max_length=2000)

    @field_validator("patient_name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        value = _WHITESPACE.sub(" ", value).strip()
        if len(value) < 2:
            raise ValueError("Please enter the patient's full name.")
        if len(value) > 80:
            raise ValueError("Please keep the name under 80 characters.")
        if not _is_valid_name(value):
            raise ValueError("Names can contain letters, spaces, dots, apostrophes and hyphens only.")
        return value

    @field_validator("department_id")
    @classmethod
    def validate_department(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Please choose a department.")
        return value

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, value: str) -> str:
        value = _WHITESPACE.sub(" ", value).strip()
        if len(value) < 10:
            raise ValueError("Please describe the reason in at least 10 characters.")
        if len(value) > 500:
            raise ValueError("Please keep the reason under 500 characters.")
        return value


class AppointmentRead(BaseModel):
    reference: str
    patient_name: str
    department_id: str
    department_name: str
    preferred_date: date
    reason: str
    status: str
    source: str
    created_at: datetime
    updated_at: datetime
    # Phase 5: filled in only after a front-desk decision.
    reviewed_by: str | None = None
    reviewed_at: datetime | None = None
    review_note: str | None = None


class FrontDeskDecision(BaseModel):
    decision: Literal["confirm", "decline"]
    note: str = Field(default="", max_length=1000)

    @field_validator("note")
    @classmethod
    def validate_note(cls, value: str) -> str:
        value = _WHITESPACE.sub(" ", value).strip()
        if len(value) > 300:
            raise ValueError("Please keep the note under 300 characters.")
        return value


class FrontDeskRequestRead(AppointmentRead):
    patient_email: str


class ActivityEventRead(BaseModel):
    id: int
    event_type: str
    actor: str
    summary: str
    reference: str | None
    created_at: datetime


# ---------- Assistant (Phase 3) ----------
class AssistantMessageRequest(BaseModel):
    message: str = Field(max_length=4000)
    conversation_id: str | None = Field(default=None, max_length=40)

    @field_validator("message")
    @classmethod
    def validate_message(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Please type a message.")
        if len(value) > 1000:
            raise ValueError("Please keep your message under 1000 characters.")
        return value


class SuggestionRead(BaseModel):
    label: str
    message: str | None = None
    href: str | None = None


class AgentStepRead(BaseModel):
    order: int
    agent: str
    action: str
    status: str
    detail: str
    data: dict
    duration_ms: int


class AgentRunRead(BaseModel):
    id: int
    conversation_id: str
    user_message: str
    detected_intent: str
    confidence: float
    classifier_method: str
    selected_agent: str
    outcome_status: str
    outcome_summary: str
    reference: str | None
    duration_ms: int
    created_at: datetime
    steps: list[AgentStepRead] = []


class AssistantReply(BaseModel):
    conversation_id: str
    run_id: int
    agent: str
    intent: str
    confidence: float
    method: str
    outcome_status: str
    reply: str
    cards: list[dict]
    suggestions: list[SuggestionRead]
    sources: list[str]
    reference: str | None
    pending_task: str | None
    run: AgentRunRead


# ---------- Symptom Guidance form (Phase 4) ----------
DurationChoice = Literal["under_1_day", "1_3_days", "4_7_days", "1_3_weeks", "over_3_weeks"]


class CareAssessRequest(BaseModel):
    symptom_ids: list[str] = Field(default_factory=list, max_length=30)
    free_text: str = Field(default="", max_length=2000)
    duration: DurationChoice | None = None
    severity: Literal["mild", "moderate", "severe"] | None = None
    age_group: Literal["infant", "child", "adult", "older_adult"] | None = None
    pregnant: bool = False
    long_term_condition: bool = False

    @field_validator("free_text")
    @classmethod
    def validate_free_text(cls, value: str) -> str:
        value = _WHITESPACE.sub(" ", value).strip()
        if len(value) > 500:
            raise ValueError("Please keep the description under 500 characters.")
        return value


class CareAssessResponse(BaseModel):
    assessment: dict
    run: AgentRunRead
