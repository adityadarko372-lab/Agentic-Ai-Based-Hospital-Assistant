"""Public hospital directory (fictional demo content). No sign-in needed."""

from typing import Any

from fastapi import APIRouter, Depends
from sqlmodel import Session, col, select

from app.db.models import Department
from app.db.session import get_session
from app.knowledge import load_hospital_info
from app.schemas import DepartmentRead

router = APIRouter(prefix="/api/hospital", tags=["hospital"])


@router.get("/departments", response_model=list[DepartmentRead])
def list_departments(session: Session = Depends(get_session)) -> list[Department]:
    return list(session.exec(select(Department).order_by(col(Department.sort_order))))


@router.get("/info")
def read_hospital_info() -> dict[str, Any]:
    """General hospital details, booking guidance and emergency numbers."""
    info = load_hospital_info()
    return {
        "notice": info["_notice"],
        "version": info["version"],
        "hospital": info["hospital"],
        "emergency_numbers": info["emergency_numbers"],
        "appointment_guidance": info["appointment_guidance"],
    }
