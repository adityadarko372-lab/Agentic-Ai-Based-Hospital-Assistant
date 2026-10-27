"""Recording and reading the patient's activity history."""

from sqlmodel import Session, col, select

from app.db.models import ActivityEvent


def record_event(
    session: Session,
    *,
    user_id: int,
    event_type: str,
    actor: str,
    summary: str,
    reference: str | None = None,
) -> ActivityEvent:
    """Add an event to the current transaction (the caller commits)."""
    event = ActivityEvent(
        user_id=user_id, event_type=event_type, actor=actor, summary=summary, reference=reference
    )
    session.add(event)
    return event


def list_events_for_user(session: Session, user_id: int, limit: int = 20) -> list[ActivityEvent]:
    statement = (
        select(ActivityEvent)
        .where(ActivityEvent.user_id == user_id)
        .order_by(col(ActivityEvent.created_at).desc(), col(ActivityEvent.id).desc())
        .limit(limit)
    )
    return list(session.exec(statement))
