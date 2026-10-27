"""Shared building blocks for every agent.

An agent receives an `AgentContext` (who is asking, what they said, the
conversation's unfinished task) and returns an `AgentResult` (the reply,
optional cards for the UI, and what should happen next). Every agent writes
its visible steps into the shared `Trace`, which is saved and shown in the
Agent Activity panel.
"""

import time
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Literal

from sqlmodel import Session

from app.db.models import Conversation, User

SUPERVISOR = "Supervisory Agent"
SAFETY_GATE = "Safety Gate"
PATIENT_ASSISTANCE = "Patient Assistance Agent"
APPOINTMENT = "Appointment Agent"
CARE_NAVIGATION = "Care Navigation Agent"

StepStatus = Literal["ok", "warning", "blocked", "fallback", "error"]
OutcomeStatus = Literal[
    "answered",
    "needs_input",
    "action_completed",
    "emergency_escalation",
    "refused",
    "clarification",
    "information_unavailable",
    "error",
]


@dataclass
class TraceStep:
    agent: str
    action: str
    status: StepStatus
    detail: str
    data: dict[str, Any]
    duration_ms: int


class Trace:
    """Ordered list of what each agent did for one message."""

    def __init__(self) -> None:
        self.steps: list[TraceStep] = []
        self._last_mark = time.perf_counter()

    def add(
        self,
        agent: str,
        action: str,
        detail: str,
        *,
        status: StepStatus = "ok",
        data: dict[str, Any] | None = None,
    ) -> None:
        now = time.perf_counter()
        elapsed = int((now - self._last_mark) * 1000)
        self._last_mark = now
        self.steps.append(TraceStep(agent, action, status, detail[:500], data or {}, elapsed))


@dataclass
class Suggestion:
    """A one-tap follow-up shown under the reply: either a message to send or a link."""

    label: str
    message: str | None = None
    href: str | None = None


@dataclass
class AgentContext:
    session: Session
    user: User
    conversation: Conversation
    message: str
    text: str  # normalised message
    state: dict[str, Any]
    trace: Trace
    today: date


@dataclass
class AgentResult:
    agent: str
    reply: str
    outcome_status: OutcomeStatus
    outcome_summary: str
    cards: list[dict[str, Any]] = field(default_factory=list)
    suggestions: list[Suggestion] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)
    reference: str | None = None
    # The unfinished task to remember for the next message (None = nothing pending).
    pending_task: str | None = None
    state: dict[str, Any] = field(default_factory=dict)
    # True when the agent already wrote its own activity event (e.g. "request submitted").
    recorded_activity: bool = False
