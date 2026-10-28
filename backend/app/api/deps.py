"""Shared FastAPI dependencies: identifying the signed-in user.

Every protected endpoint depends on `get_current_patient`, so access control
is enforced by the backend on each request, never by the user interface.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import Session

from app.core.security import read_session_token
from app.db.models import User, UserRole
from app.db.session import get_session

_bearer_scheme = HTTPBearer(auto_error=False)

_NOT_SIGNED_IN = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Please sign in to continue.",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    session: Session = Depends(get_session),
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise _NOT_SIGNED_IN
    user_id = read_session_token(credentials.credentials)
    if user_id is None:
        raise _NOT_SIGNED_IN
    user = session.get(User, user_id)
    if user is None:
        raise _NOT_SIGNED_IN
    return user


def get_current_patient(user: User = Depends(get_current_user)) -> User:
    if user.role != UserRole.PATIENT:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This action is only available to patients.")
    return user


def get_current_front_desk(user: User = Depends(get_current_user)) -> User:
    """Front-desk staff only, and only when FRONT_DESK_ENABLED is on."""
    from app.core.config import get_settings

    if not get_settings().front_desk_enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Front-desk review is switched off.")
    if user.role != UserRole.FRONT_DESK:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This page is only for hospital front-desk staff.")
    return user
