"""Demo data loaded at start-up.

- Departments are synchronised from app/knowledge/hospital_info.json every
  start, so editing the JSON updates the directory.
- Demo patients are created only if they do not exist yet. Their requests and
  history are never touched by seeding.

All people here are fictional. The shared demo password is documented in the
README because this is a local demonstration, not a real account system.
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


def seed_demo_patients(session: Session) -> None:
    for patient in DEMO_PATIENTS:
        exists = session.exec(select(User).where(User.email == patient["email"])).first()
        if exists is None:
            session.add(
                User(
                    email=patient["email"],
                    full_name=patient["full_name"],
                    password_hash=hash_password(DEMO_PASSWORD),
                    role=UserRole.PATIENT,
                )
            )
    session.commit()


def seed_all(session: Session) -> None:
    seed_departments(session)
    seed_demo_patients(session)
