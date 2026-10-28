"""Front-desk review endpoints (Phase 5, behind FRONT_DESK_ENABLED).

GET  /api/front-desk/requests?status=pending     requests to review (all patients)
POST /api/front-desk/requests/{reference}/decision   confirm or decline (once)
"""

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session

from app.api.deps import get_current_front_desk
from app.db.models import AppointmentRequest, Department, User
from app.db.session import get_session
from app.schemas import FrontDeskDecision, FrontDeskRequestRead
from app.services import front_desk_service
from app.services.appointment_service import AppointmentConflict, AppointmentNotFound, to_appointment_read

router = APIRouter(prefix="/api/front-desk", tags=["front-desk"])


def _to_read(appointment: AppointmentRequest, department: Department, patient: User) -> FrontDeskRequestRead:
    return FrontDeskRequestRead(**to_appointment_read(appointment, department).model_dump(), patient_email=patient.email)


@router.get("/requests", response_model=list[FrontDeskRequestRead])
def list_requests(
    status: Literal["pending", "confirmed", "declined", "cancelled", "all"] = Query(default="pending"),
    _staff: User = Depends(get_current_front_desk),
    session: Session = Depends(get_session),
) -> list[FrontDeskRequestRead]:
    rows = front_desk_service.list_requests(session, None if status == "all" else status)
    return [_to_read(*row) for row in rows]


@router.post("/requests/{reference}/decision", response_model=FrontDeskRequestRead)
def decide(
    reference: str,
    body: FrontDeskDecision,
    staff: User = Depends(get_current_front_desk),
    session: Session = Depends(get_session),
) -> FrontDeskRequestRead:
    try:
        return _to_read(*front_desk_service.decide(session, staff, reference, body.decision, body.note))
    except AppointmentNotFound as missing:
        raise HTTPException(status_code=404, detail="Appointment request not found.") from missing
    except AppointmentConflict as conflict:
        raise HTTPException(status_code=409, detail=str(conflict)) from conflict
