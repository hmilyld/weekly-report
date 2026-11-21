"""Auth router: login, setup, password change."""

import logging
import time
from threading import Lock

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import exists, insert, literal, select
from sqlalchemy.orm import Session

from .. import crud
from ..auth import (
    create_access_token,
    get_current_user,
    hash_password,
    validate_password,
    verify_password,
    verify_password_safe,
)
from ..database import get_db
from ..envelope import ensure_user_dek, provision_user_dek
from ..migration import migrate_user_to_dek
from ..models import User
from ..schemas import (
    LoginRequest,
    PasswordChange,
    SetupRequest,
    SetupStatus,
    TokenResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


# ─── Rate limiter (in-memory, per process) ───────────────
# Only failed attempts are recorded, so a legitimate user is never locked out by
# logging in repeatedly; keys expire with their window and the map is capped so
# spraying usernames cannot grow it without bound.

_MAX_ATTEMPTS = 5
_WINDOW_SECONDS = 60
_MAX_TRACKED_KEYS = 2048

_rate_lock = Lock()
_attempts: dict[str, list[float]] = {}


def _prune_locked(now: float) -> None:
    stale = [
        key
        for key, stamps in _attempts.items()
        if not stamps or now - stamps[-1] >= _WINDOW_SECONDS
    ]
    for key in stale:
        del _attempts[key]
    overflow = len(_attempts) - _MAX_TRACKED_KEYS
    if overflow > 0:
        oldest = sorted(_attempts.items(), key=lambda item: item[1][-1] if item[1] else 0.0)
        for key, _ in oldest[:overflow]:
            del _attempts[key]


def _ensure_not_limited(key: str) -> None:
    """Raise 429 when the key already recorded _MAX_ATTEMPTS failures in the window."""
    now = time.monotonic()
    with _rate_lock:
        recent = [stamp for stamp in _attempts.get(key, []) if now - stamp < _WINDOW_SECONDS]
        if recent:
            _attempts[key] = recent
        else:
            _attempts.pop(key, None)
        _prune_locked(now)
        if len(recent) >= _MAX_ATTEMPTS:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Too many attempts. Try again in {_WINDOW_SECONDS} seconds.",
            )


def _record_failure(key: str) -> None:
    now = time.monotonic()
    with _rate_lock:
        stamps = _attempts.setdefault(key, [])
        stamps.append(now)
        if len(stamps) > _MAX_ATTEMPTS:
            del stamps[:-_MAX_ATTEMPTS]


def _rate_limit_keys(request: Request, username: str) -> tuple[str, str]:
    client_ip = request.client.host if request.client else "unknown"
    return f"login:ip:{client_ip}", f"login:user:{username.strip().lower()}"


# ─── Endpoints ──────────────────────────────────────────


@router.get("/status", response_model=SetupStatus)
def get_auth_status(db: Session = Depends(get_db)):
    """Check if initial setup is needed (no users exist yet)."""
    return SetupStatus(needs_setup=db.query(User).count() == 0)


@router.post("/setup", response_model=TokenResponse)
def initial_setup(body: SetupRequest, db: Session = Depends(get_db)):
    """Create the first user account. Only works when no users exist."""
    username = body.username.strip()
    if not username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username cannot be empty",
        )
    validate_password(body.password)

    # Single atomic statement: the guard and the insert cannot interleave, so two
    # concurrent setup requests cannot both create an admin.
    stmt = insert(User).from_select(
        ["username", "password_hash", "role", "password_version", "needs_encryption_migration"],
        select(
            literal(username),
            literal(hash_password(body.password)),
            literal("admin"),
            literal(0),
            literal(False),
        ).where(~exists(select(User.id))),
    )
    inserted = db.execute(stmt).rowcount
    if not inserted:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Setup has already been completed",
        )
    db.commit()

    user = crud.get_user_by_username(db, username)
    if user is None:  # pragma: no cover — the insert above just created it
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Setup failed"
        )
    crud.touch_last_login(db, user)
    provision_user_dek(db, user)
    token = create_access_token({"sub": str(user.id), "username": user.username, "pwd_ver": 0})
    return TokenResponse(access_token=token)


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, request: Request, db: Session = Depends(get_db)):
    ip_key, user_key = _rate_limit_keys(request, body.username)
    _ensure_not_limited(ip_key)
    _ensure_not_limited(user_key)

    user = crud.get_user_by_username(db, body.username)
    password_ok = verify_password_safe(body.password, user.password_hash if user else None)
    if not user or not password_ok:
        _record_failure(ip_key)
        _record_failure(user_key)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    token = create_access_token(
        {"sub": str(user.id), "username": user.username, "pwd_ver": user.password_version or 0}
    )

    crud.touch_last_login(db, user)

    # Content keys are decoupled from the login password (envelope encryption).
    # Migrated users: the DEK is normally already cached from startup; unwrap
    # on demand. A failure here must not block authentication itself.
    if user.wrapped_dek:
        try:
            ensure_user_dek(db, user)
        except Exception:
            logger.exception("Failed to unwrap DEK for user %d at login", user.id)
    else:
        # Legacy user: one-time migration, only possible now that we have the
        # password to derive the old key. Failure rolls back and must NOT lock
        # the account out: authentication is decoupled from content keys.
        # wrapped_dek stays NULL — reads are flagged, writes answer 409 — and
        # the next login retries. The failing record is identified in the log.
        try:
            migrate_user_to_dek(db, user, body.password)
        except Exception:
            logger.exception(
                "Envelope migration failed for user %d; login proceeds without a content key",
                user.id,
            )

    return TokenResponse(access_token=token)


@router.post("/change-password", response_model=TokenResponse)
def change_password(
    body: PasswordChange,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not verify_password(body.old_password, user.password_hash):
        # 402: the session is still valid, only the re-supplied password is wrong.
        # (401 would make the client drop the session and ask for a full re-login.)
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="当前密码不正确",
        )
    validate_password(body.new_password)

    # Envelope encryption: content is encrypted with a per-user DEK that is
    # independent of the login password, so changing the password only updates
    # the hash and bumps password_version — ciphertext is never touched.
    new_hash = hash_password(body.new_password)
    crud.change_password(db, user, new_hash)

    # Changing the password bumps password_version, which invalidates the current
    # token. Hand back a fresh one so the person who changed it stays signed in;
    # every other session is signed out. API tokens are NOT revoked here — clients
    # can drop them explicitly via DELETE /api/v1/tokens.
    token = create_access_token(
        {"sub": str(user.id), "username": user.username, "pwd_ver": user.password_version}
    )
    return TokenResponse(access_token=token)


@router.post("/logout")
def logout(user: User = Depends(get_current_user)):
    # The DEK is a server-side key recoverable from the DB at any time; it is
    # NOT per-session. Clearing it here would break every other device of the
    # same account, so logout only ends the session (client drops the token).
    return {"message": "Logged out successfully"}
