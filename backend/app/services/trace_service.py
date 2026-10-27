"""Reading saved agent runs and their steps (the Agent Activity history)."""

import json

from sqlmodel import Session, col, select

from app.core.clock import as_utc
from app.db.models import AgentRun, AgentStep
from app.schemas import AgentRunRead, AgentStepRead


def to_run_read(run: AgentRun, steps: list[AgentStep]) -> AgentRunRead:
    assert run.id is not None
    return AgentRunRead(
        id=run.id,
        conversation_id=run.conversation_id,
        user_message=run.user_message,
        detected_intent=run.detected_intent,
        confidence=run.confidence,
        classifier_method=run.classifier_method,
        selected_agent=run.selected_agent,
        outcome_status=run.outcome_status,
        outcome_summary=run.outcome_summary,
        reference=run.reference,
        duration_ms=run.duration_ms,
        created_at=as_utc(run.created_at),
        steps=[
            AgentStepRead(
                order=step.step_order,
                agent=step.agent,
                action=step.action,
                status=step.status,
                detail=step.detail,
                data=json.loads(step.data_json or "{}"),
                duration_ms=step.duration_ms,
            )
            for step in sorted(steps, key=lambda s: s.step_order)
        ],
    )


def _steps_for(session: Session, run_ids: list[int]) -> dict[int, list[AgentStep]]:
    grouped: dict[int, list[AgentStep]] = {run_id: [] for run_id in run_ids}
    if run_ids:
        for step in session.exec(select(AgentStep).where(col(AgentStep.run_id).in_(run_ids))):
            grouped[step.run_id].append(step)
    return grouped


def list_runs(
    session: Session,
    user_id: int,
    *,
    limit: int = 30,
    agent: str | None = None,
    conversation_id: str | None = None,
    newest_first: bool = True,
) -> list[AgentRunRead]:
    statement = select(AgentRun).where(AgentRun.user_id == user_id)
    if agent:
        statement = statement.where(AgentRun.selected_agent == agent)
    if conversation_id:
        statement = statement.where(AgentRun.conversation_id == conversation_id)
    order = col(AgentRun.id).desc() if newest_first else col(AgentRun.id).asc()
    runs = list(session.exec(statement.order_by(order).limit(limit)))
    steps = _steps_for(session, [run.id for run in runs if run.id is not None])
    return [to_run_read(run, steps.get(run.id or 0, [])) for run in runs]


def get_run(session: Session, user_id: int, run_id: int) -> AgentRunRead | None:
    run = session.get(AgentRun, run_id)
    if run is None or run.user_id != user_id:
        return None
    steps = _steps_for(session, [run_id])[run_id]
    return to_run_read(run, steps)
