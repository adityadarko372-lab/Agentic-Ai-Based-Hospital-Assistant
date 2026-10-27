"""The signed-in patient's history.

GET /api/activity/mine        readable events (dashboard "Recent activity")
GET /api/activity/runs        agent runs: which agent handled each request (Agent Activity page)
GET /api/activity/runs/{id}   one run with every step
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session

from app.api.deps import get_current_patient
from app.core.clock import as_utc
from app.db.models import User
from app.db.session import get_session
from app.schemas import ActivityEventRead, AgentRunRead
from app.services.activity_service import list_events_for_user
from app.services.trace_service import get_run, list_runs

router = APIRouter(prefix="/api/activity", tags=["activity"])


@router.get("/runs", response_model=list[AgentRunRead])
def list_my_agent_runs(
    limit: int = Query(default=30, ge=1, le=100),
    agent: str | None = Query(default=None, max_length=60),
    patient: User = Depends(get_current_patient),
    session: Session = Depends(get_session),
) -> list[AgentRunRead]:
    """Which agent handled each of your assistant requests, with every step."""
    assert patient.id is not None
    return list_runs(session, patient.id, limit=limit, agent=agent)


@router.get("/runs/{run_id}", response_model=AgentRunRead)
def read_my_agent_run(
    run_id: int, patient: User = Depends(get_current_patient), session: Session = Depends(get_session)
) -> AgentRunRead:
    assert patient.id is not None
    run = get_run(session, patient.id, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found.")
    return run


@router.get("/mine", response_model=list[ActivityEventRead])
def list_my_activity(
    limit: int = Query(default=20, ge=1, le=100),
    patient: User = Depends(get_current_patient),
    session: Session = Depends(get_session),
) -> list[ActivityEventRead]:
    assert patient.id is not None
    return [
        ActivityEventRead(
            id=event.id or 0,
            event_type=event.event_type,
            actor=event.actor,
            summary=event.summary,
            reference=event.reference,
            created_at=as_utc(event.created_at),
        )
        for event in list_events_for_user(session, patient.id, limit)
    ]
