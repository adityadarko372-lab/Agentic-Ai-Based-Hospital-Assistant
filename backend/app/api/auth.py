"""Demo login: POST /api/auth/login and GET /api/auth/me.

Sign-out is handled by the browser discarding its token (tokens are
stateless and expire after SESSION_HOURS).
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.api.deps import get_current_user
from app.core.clock import as_utc
from app.core.security import create_session_token, verify_password
from app.db.models import User
from app.db.session import get_session
from app.schemas import LoginRequest, LoginResponse, UserRead

router = APIRouter(prefix="/api/auth", tags=["auth"])

# The same message for "unknown email" and "wrong password", so the login
# form cannot be used to discover which accounts exist.
_INVALID_LOGIN = "Incorrect email or password."


def to_user_read(user: User) -> UserRead:
    assert user.id is not None
    return UserRead(id=user.id, email=user.email, full_name=user.full_name, role=user.role)


@router.post("/login", response_model=LoginResponse)
def login(credentials: LoginRequest, session: Session = Depends(get_session)) -> LoginResponse:
    user = session.exec(select(User).where(User.email == credentials.email)).first()
    if user is None or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=_INVALID_LOGIN)

    assert user.id is not None
    token, expires_at = create_session_token(user.id)
    return LoginResponse(access_token=token, expires_at=as_utc(expires_at), user=to_user_read(user))


@router.get("/me", response_model=UserRead)
def read_me(user: User = Depends(get_current_user)) -> UserRead:
    return to_user_read(user)
