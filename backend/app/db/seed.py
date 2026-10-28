"""Demo data loaded at start-up.

- Departments are synchronised from app/knowledge/hospital_info.json every
  start, so editing the JSON updates the directory.
- Demo accounts are created only if they do not exist yet. Their requests and
  history are never touched by seeding.

These are demonstration accounts with synthetic data only. The shared demo
password is documented in the README because this is a local demonstration,
not a real account system.
"""

from sqlmodel import Session, select

from app.core.security import hash_password
from app.db.models import Department, User, UserRole
from app.knowledge import load_hospital_info

DEMO_PASSWORD = "NovaDemo@2026"

DEMO_PATIENTS = [
    {"email": "patient@novahealth.demo", "full_name": "Asha Verma"},
    {"email": "rohan.mehta@novahealth.demo", "full_name": "Rohan Mehta"},
    {"email": "kavya.iyer@novahealth.demo", "full_name": "Kavya Iyer"},
    # Phase 5: project-team demo accounts (synthetic data only).
    {"email": "aditya.singh@novahealth.demo", "full_name": "Aditya Singh"},
    {"email": "aaryan.naik@novahealth.demo", "full_name": "Aaryan Naik"},
    {"email": "bhavish.keni@novahealth.demo", "full_name": "Bhavish Keni"},
]

# Phase 5: hospital staff account for the front-desk review page.
DEMO_STAFF = [
    {"email": "frontdesk@novahealth.demo", "full_name": "Meera Desai", "role": UserRole.FRONT_DESK},
]


def seed_departments(session: Session) -> None:
    departments = load_hospital_info()["departments"]
    for sort_order, record in enumerate(departments):
        existing = session.get(Department, record["id"])
        values = {**record, "sort_order": sort_order}
        if existing is None:
            session.add(Department(**values))
        else:
            for key, value in values.items():
                setattr(existing, key, value)
    session.commit()


def _ensure_user(session: Session, email: str, full_name: str, role: UserRole) -> None:
    if session.exec(select(User).where(User.email == email)).first() is None:
        session.add(User(email=email, full_name=full_name, password_hash=hash_password(DEMO_PASSWORD), role=role))


def seed_demo_patients(session: Session) -> None:
    for patient in DEMO_PATIENTS:
        _ensure_user(session, patient["email"], patient["full_name"], UserRole.PATIENT)
    for staff in DEMO_STAFF:
        _ensure_user(session, staff["email"], staff["full_name"], staff["role"])
    session.commit()


def seed_all(session: Session) -> None:
    seed_departments(session)
    seed_demo_patients(session)
