"""The signed-in patient's activity history (dashboard "Recent activity")."""

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from app.api.deps import get_current_patient
from app.core.clock import as_utc
from app.db.models import User
from app.db.session import get_session
from app.schemas import ActivityEventRead
from app.services.activity_service import list_events_for_user

router = APIRouter(prefix="/api/activity", tags=["activity"])


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
