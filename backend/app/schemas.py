"""Request and response shapes for the HTTP API.

Validators return short, friendly messages because they are shown directly
to patients next to the form field (see app/core/errors.py).
"""

import re
import unicodedata
from datetime import date, datetime

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


class ActivityEventRead(BaseModel):
    id: int
    event_type: str
    actor: str
    summary: str
    reference: str | None
    created_at: datetime
