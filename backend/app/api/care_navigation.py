"""Preliminary Symptom Guidance endpoints (Module 4).

GET  /api/care-navigation/options   the form's choices (public; no personal data)
POST /api/care-navigation/assess    evaluate the form with the shared care engine
"""

from typing import Any

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.api.deps import get_current_patient
from app.db.models import User
from app.db.session import get_session
from app.schemas import CareAssessRequest, CareAssessResponse
from app.services import care_service
from app.services.trace_service import to_run_read

router = APIRouter(prefix="/api/care-navigation", tags=["care-navigation"])


@router.get("/options")
def read_form_options() -> dict[str, Any]:
    return care_service.form_options()


@router.post("/assess", response_model=CareAssessResponse)
def assess_symptoms(
    data: CareAssessRequest,
    patient: User = Depends(get_current_patient),
    session: Session = Depends(get_session),
) -> CareAssessResponse:
    assessment, run, steps = care_service.assess(session, patient, data)
    return CareAssessResponse(assessment=care_service.assessment_to_dict(assessment), run=to_run_read(run, steps))
