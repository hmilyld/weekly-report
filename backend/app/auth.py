"""JWT authentication helpers."""

import re
from datetime import UTC, datetime, timedelta
from threading import Lock

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from .config import settings
from .crypto import derive_key
from .database import get_db
from .models import ApiToken, User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
# Dual-auth variant: does not raise when the Authorization header is absent, so
# the dependency can answer 401 itself (401 = not authenticated, 403 = wrong role).
_bearer_or_token = HTTPBearer(auto_error=False)

# bcrypt silently truncates anything past 72 bytes, so a longer password would
# be equivalent to its 72-byte prefix. Reject instead of truncating.
BCRYPT_MAX_PASSWORD_BYTES = 72

# Don't rewrite last_used_at on every token request: SQLite commits are
# fsync-bound and Android polls frequently. Update at most this often.
TOKEN_USAGE_UPDATE_INTERVAL_SECONDS = 300

_dummy_hash: str | None = None
_dummy_hash_lock = Lock()


def _get_dummy_hash() -> str:
    """A throwaway hash used to keep unknown-user logins as slow as real ones."""
    global _dummy_hash
    if _dummy_hash is None:
        with _dummy_hash_lock:
            if _dummy_hash is None:
                _dummy_hash = pwd_context.hash("timing-equalizer-not-a-real-password")
    return _dummy_hash


def _last_used_is_stale(last_used: datetime | None, now: datetime) -> bool:
    """True when the token's usage timestamp is old enough to be rewritten.

    SQLite stores datetimes without an offset (UTC by convention), so a value
    read back is naive and must be compared as UTC.
    """
    if last_used is None:
        return True
    if last_used.tzinfo is None:
        last_used = last_used.replace(tzinfo=UTC)
    return (now - last_used).total_seconds() > TOKEN_USAGE_UPDATE_INTERVAL_SECONDS


# ─── Password validation ────────────────────────────────

_WEAK_PASSWORDS = {
    "11111111",
    "12345678",
    "password",
    "qwerty123",
    "abc12345",
    "123456789",
    "1234567890",
    "admin123",
    "letmein1",
}


def validate_password(password: str) -> None:
    """Enforce minimum password complexity."""
    if password.lower() in _WEAK_PASSWORDS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password is too common. Please choose a stronger password.",
        )
    if not re.search(r"[A-Za-z]", password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must contain at least one letter.",
        )
    if not re.search(r"\d", password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must contain at least one digit.",
        )
    if len(password.encode("utf-8")) > BCRYPT_MAX_PASSWORD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Password must be at most {BCRYPT_MAX_PASSWORD_BYTES} bytes (UTF-8).",
        )


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def verify_password_safe(plain: str, hashed: str | None) -> bool:
    """Verify a password, spending the same bcrypt cost when the user is unknown.

    Without the dummy verification, a missing username answers much faster than
    a wrong password and leaks which accounts exist.
    """
    if hashed is None:
        pwd_context.verify(plain, _get_dummy_hash())
        return False
    return pwd_context.verify(plain, hashed)


def derive_user_key(password: str, user: User) -> bytes:
    """LEGACY password-derived content key — migration ONLY.

    Pre-envelope data was encrypted with this key. Its parameters (fixed salt,
    PBKDF2-SHA256 100k) are FROZEN: any change makes legacy ciphertext
    permanently unreadable. New content uses the per-user DEK (envelope.py);
    the login password no longer derives content keys.
    """
    salt = f"user_{user.id}_encryption_salt".encode().ljust(32, b"\0")[:32]
    return derive_key(password, salt)


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(UTC) + (expires_delta or timedelta(minutes=settings.jwt_expire_minutes))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError as err:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from err


def _user_from_jwt(raw_token: str, db: Session) -> User:
    """Resolve a user from a JWT, enforcing password-version invalidation."""
    payload = decode_token(raw_token)
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload"
        )
    try:
        uid = int(user_id)
    except (ValueError, TypeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload"
        ) from exc
    user = db.query(User).filter(User.id == uid).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    # Every token must carry the password version it was minted with; a token
    # without the claim is treated as version 0, so changing the password
    # invalidates it too (an absent claim must never be a permanent bypass).
    try:
        token_pwd_ver = int(payload.get("pwd_ver", 0))
    except (ValueError, TypeError):
        token_pwd_ver = -1
    current_pwd_ver = getattr(user, "password_version", 0) or 0
    if token_pwd_ver != current_pwd_ver:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Password has been changed. Please log in again.",
        )
    return user


def _user_from_api_token(raw_token: str, db: Session) -> User:
    """Resolve a user from an X-API-Token value, recording its last use.

    The usage write stays on the request session and is committed by ``get_db``
    when the request succeeds, so a GET never opens a second transaction.
    """
    api_token = db.query(ApiToken).filter(ApiToken.token == raw_token).first()
    if not api_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API token")
    now = datetime.now(UTC)
    if _last_used_is_stale(api_token.last_used_at, now):
        api_token.last_used_at = now
    user = db.query(User).filter(User.id == api_token.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token owner not found"
        )
    return user


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_or_token),
    db: Session = Depends(get_db),
) -> User:
    """JWT-only dependency (admin/auth endpoints). Rejects API tokens with 401."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return _user_from_jwt(credentials.credentials, db)


def get_authenticated_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_or_token),
    x_api_token: str | None = Header(default=None, alias="X-API-Token"),
    db: Session = Depends(get_db),
) -> User:
    """Dual-auth dependency for data endpoints: JWT or X-API-Token.

    JWT wins when both are supplied. Admin/config endpoints keep
    `get_current_user`/`require_admin`, so API tokens are structurally
    limited to data access.
    """
    if credentials is not None:
        return _user_from_jwt(credentials.credentials, db)
    if x_api_token:
        return _user_from_api_token(x_api_token, db)
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )


def require_admin(user: User = Depends(get_current_user)) -> User:
    """Require the current user to have admin role."""
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return user
