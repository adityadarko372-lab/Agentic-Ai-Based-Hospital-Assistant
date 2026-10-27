"""AI Hospital Assistant endpoints (Modules 2 and 3).

POST /api/assistant/message                    send a message; the Supervisory Agent handles it
GET  /api/assistant/conversations/{id}         the messages of one of your conversations
"""

from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.agents.supervisor import ConversationNotFound, handle_message
from app.api.deps import get_current_patient
from app.db.models import Conversation, User
from app.db.session import get_session
from app.schemas import AgentRunRead, AssistantMessageRequest, AssistantReply, SuggestionRead
from app.services.trace_service import list_runs, to_run_read

router = APIRouter(prefix="/api/assistant", tags=["assistant"])


@router.post("/message", response_model=AssistantReply)
def send_message(
    body: AssistantMessageRequest,
    patient: User = Depends(get_current_patient),
    session: Session = Depends(get_session),
) -> AssistantReply:
    try:
        turn = handle_message(session, patient, body.message, body.conversation_id)
    except ConversationNotFound as missing:
        raise HTTPException(status_code=404, detail="Conversation not found. Please start a new conversation.") from missing

    result = turn.result
    return AssistantReply(
        conversation_id=turn.conversation_id,
        run_id=turn.run.id or 0,
        agent=result.agent,
        intent=turn.intent.intent,
        confidence=turn.intent.confidence,
        method=turn.intent.method,
        outcome_status=result.outcome_status,
        reply=result.reply,
        cards=result.cards,
        suggestions=[SuggestionRead(**asdict(s)) for s in result.suggestions],
        sources=result.sources,
        reference=result.reference,
        pending_task=result.pending_task,
        run=to_run_read(turn.run, turn.steps),
    )


@router.get("/conversations/{conversation_id}", response_model=list[AgentRunRead])
def read_conversation(
    conversation_id: str,
    patient: User = Depends(get_current_patient),
    session: Session = Depends(get_session),
) -> list[AgentRunRead]:
    conversation = session.get(Conversation, conversation_id)
    if conversation is None or conversation.user_id != patient.id:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    assert patient.id is not None
    return list_runs(session, patient.id, conversation_id=conversation_id, limit=100, newest_first=False)
