"""Password hashing and signed session tokens for the demo login.

- Passwords are hashed with bcrypt (salted, deliberately slow).
- A session token is a JWT signed with HMAC-SHA256 using SESSION_SECRET. It
  holds only the user id and an expiry time, never personal data.

This is adequate for a local demonstration. A production system would add
token revocation, rate limiting, account lockout and an identity provider.
"""

from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.core.config import get_settings

TOKEN_ALGORITHM = "HS256"
# bcrypt only uses the first 72 bytes of a password; longer input is refused.
_BCRYPT_MAX_BYTES = 72


def hash_password(plain_password: str) -> str:
    rounds = get_settings().bcrypt_rounds
    return bcrypt.hashpw(plain_password.encode("utf-8"), bcrypt.gensalt(rounds=rounds)).decode("utf-8")


def verify_password(plain_password: str, password_hash: str) -> bool:
    encoded = plain_password.encode("utf-8")
    if len(encoded) > _BCRYPT_MAX_BYTES:
        return False
    try:
        return bcrypt.checkpw(encoded, password_hash.encode("utf-8"))
    except ValueError:
        return False


def create_session_token(user_id: int) -> tuple[str, datetime]:
    settings = get_settings()
    expires_at = datetime.now(timezone.utc) + timedelta(hours=settings.session_hours)
    payload = {"sub": str(user_id), "exp": expires_at, "iat": datetime.now(timezone.utc)}
    token = jwt.encode(payload, settings.session_secret, algorithm=TOKEN_ALGORITHM)
    return token, expires_at


def read_session_token(token: str) -> int | None:
    """Return the user id inside a valid token, or None if it is invalid or expired."""
    try:
        payload = jwt.decode(
            token,
            get_settings().session_secret,
            algorithms=[TOKEN_ALGORITHM],  # never accept "none" or other algorithms
            options={"require": ["exp", "sub"]},
        )
        return int(payload["sub"])
    except (jwt.InvalidTokenError, ValueError):
        return None
