"""Appointment request endpoints (Module 5). Patients only see their own requests."""

import re
import uuid

from fastapi import APIRouter, Depends, Header, HTTPException, Response, status
from sqlmodel import Session

from app.api.deps import get_current_patient
from app.db.models import User
from app.db.session import get_session
from app.schemas import AppointmentCreate, AppointmentRead
from app.services import appointment_service
from app.services.appointment_service import AppointmentConflict, AppointmentNotFound, to_appointment_read

router = APIRouter(prefix="/api/appointments", tags=["appointments"])

_IDEMPOTENCY_KEY_PATTERN = re.compile(r"^[A-Za-z0-9_-]{8,80}$")


@router.post(
    "",
    response_model=AppointmentRead,
    status_code=status.HTTP_201_CREATED,
    responses={200: {"description": "Duplicate submission: the original request is returned"}},
)
def create_appointment_request(
    data: AppointmentCreate,
    response: Response,
    patient: User = Depends(get_current_patient),
    session: Session = Depends(get_session),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> AppointmentRead:
    if idempotency_key is None:
        idempotency_key = uuid.uuid4().hex
    elif not _IDEMPOTENCY_KEY_PATTERN.match(idempotency_key):
        raise HTTPException(status_code=400, detail="Invalid Idempotency-Key header.")

    try:
        result = appointment_service.submit_request(session, patient, data, idempotency_key)
    except AppointmentConflict as conflict:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(conflict)) from conflict

    if not result.created:
        response.status_code = status.HTTP_200_OK
    return to_appointment_read(result.appointment, result.department)


@router.get("/mine", response_model=list[AppointmentRead])
def list_my_appointment_requests(
    patient: User = Depends(get_current_patient), session: Session = Depends(get_session)
) -> list[AppointmentRead]:
    assert patient.id is not None
    rows = appointment_service.list_requests_for_patient(session, patient.id)
    return [to_appointment_read(appointment, department) for appointment, department in rows]


@router.post("/{reference}/cancel", response_model=AppointmentRead)
def cancel_appointment_request(
    reference: str, patient: User = Depends(get_current_patient), session: Session = Depends(get_session)
) -> AppointmentRead:
    try:
        appointment, department = appointment_service.cancel_request(session, patient, reference)
    except AppointmentNotFound as missing:
        raise HTTPException(status_code=404, detail="Appointment request not found.") from missing
    except AppointmentConflict as conflict:
        raise HTTPException(status_code=409, detail=str(conflict)) from conflict
    return to_appointment_read(appointment, department)
