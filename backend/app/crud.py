"""CRUD operations."""

import base64
import hashlib
import logging
from datetime import UTC, date, datetime

from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import set_committed_value

from . import models
from .crypto import decrypt_content
from .date_range import week_bounds
from .encryption_utils import (
    decrypt_model_content,
    decrypt_record_content,
    encrypt_model_content,
)
from .envelope import CONFIG_SECRET_PREFIX, unwrap_config_secret, wrap_config_secret
from .key_cache import key_cache

logger = logging.getLogger(__name__)


def _get_legacy_api_key_encryption_key() -> bytes:
    """LEGACY: derive the old API-key encryption key from the JWT secret.

    Kept only to read pre-envelope values; new writes use envelope wrapping.
    """
    from .config import settings

    return hashlib.pbkdf2_hmac(
        "sha256",
        settings.jwt_secret_key.encode(),
        b"api_key_encryption_salt",
        100000,
        dklen=32,
    )


def _looks_like_legacy_encrypted(value: str) -> bool:
    """True if value matches the legacy base64('ct:nonce:tag') format."""
    try:
        decoded = base64.b64decode(value, validate=True).decode("utf-8")
    except Exception:
        return False
    return decoded.count(":") == 2


def encrypt_api_key(api_key: str) -> str | None:
    """Envelope-encrypt the LLM API key for storage (survives restarts)."""
    if not api_key:
        return None
    return wrap_config_secret(api_key)


def decrypt_api_key(encrypted_api_key: str) -> str | None:
    """Decrypt a stored LLM API key (envelope format, with legacy fallback)."""
    if not encrypted_api_key:
        return None
    if encrypted_api_key.startswith(CONFIG_SECRET_PREFIX):
        try:
            return unwrap_config_secret(encrypted_api_key)
        except Exception:
            logger.error(
                "Failed to unwrap LLM API key — check ENCRYPTION_MASTER_KEY; "
                "re-save the key in Settings to repair."
            )
            return None
    if not _looks_like_legacy_encrypted(encrypted_api_key):
        # Very old installs stored the key as plaintext; pass through so it
        # keeps working and gets re-wrapped by migrate_app_config_secret().
        return encrypted_api_key
    try:
        decoded = base64.b64decode(encrypted_api_key).decode()
        ciphertext, nonce, tag = decoded.split(":")
        return decrypt_content(
            {"ciphertext": ciphertext, "nonce": nonce, "tag": tag},
            _get_legacy_api_key_encryption_key(),
        )
    except Exception:
        logger.warning(
            "Legacy LLM API key could not be decrypted (JWT secret changed?); "
            "re-save the key in Settings."
        )
        return None


def _encrypt_and_set_content(model, content: str, user_id: int) -> None:
    """Encrypt content and set all encryption fields on a model instance."""
    encrypt_model_content(model, content, user_id)


def _save_encrypted_report(
    db: Session,
    model_class,
    existing,
    user_id: int,
    content: str,
    model_name: str,
    **kwargs,
):
    """Generic save function for encrypted reports (weekly/monthly)."""
    if existing:
        existing.model_name = model_name
        _encrypt_and_set_content(existing, content, user_id)
        existing.generated_at = datetime.now(UTC)
        db.commit()
        db.refresh(existing)
        _decrypt_model_content(existing, user_id)
        return existing

    report = model_class(user_id=user_id, model_name=model_name, **kwargs)
    _encrypt_and_set_content(report, content, user_id)
    db.add(report)
    db.commit()
    db.refresh(report)
    _decrypt_model_content(report, user_id)
    return report


# ─── User ───────────────────────────────────────────────


def get_user_by_username(db: Session, username: str) -> models.User | None:
    return db.query(models.User).filter(models.User.username == username).first()


def create_user(db: Session, username: str, password_hash: str, role: str = "user") -> models.User:
    user = models.User(username=username, password_hash=password_hash, role=role)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def change_password(db: Session, user: models.User, new_hash: str) -> None:
    user.password_hash = new_hash
    user.password_version = (user.password_version or 0) + 1
    db.commit()


def touch_last_login(db: Session, user: models.User) -> None:
    """Record a successful sign-in."""
    user.last_login_at = datetime.now(UTC)
    db.commit()


def get_all_users(db: Session) -> list[models.User]:
    return db.query(models.User).order_by(models.User.id).all()


def delete_user(db: Session, user_id: int) -> bool:
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        return False
    # Cascade delete related records
    db.query(models.DailyReport).filter(models.DailyReport.user_id == user_id).delete()
    db.query(models.WeeklyReport).filter(models.WeeklyReport.user_id == user_id).delete()
    db.query(models.MonthlyReport).filter(models.MonthlyReport.user_id == user_id).delete()
    db.query(models.Task).filter(models.Task.user_id == user_id).delete()
    # Delete API tokens (import here to avoid circular import)
    from .models_token import ApiToken

    db.query(ApiToken).filter(ApiToken.user_id == user_id).delete()
    db.delete(user)
    db.commit()
    # Drop the cached DEK too: SQLite reuses the highest rowid, so a later user
    # could otherwise inherit a stale key entry for this id.
    key_cache.remove(user_id)
    return True


def update_user_role(db: Session, user_id: int, role: str) -> models.User | None:
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        return None
    user.role = role
    db.commit()
    db.refresh(user)
    return user


# ─── Daily Report ───────────────────────────────────────


def get_daily_report(db: Session, user_id: int, report_date: date) -> models.DailyReport | None:
    return (
        db.query(models.DailyReport)
        .filter(models.DailyReport.user_id == user_id, models.DailyReport.date == report_date)
        .first()
    )


def _decrypt_model_content(model, user_id: int):
    """Decrypt content_encrypted back into content on a model instance.

    Delegates to encryption_utils.decrypt_model_content; on failure sets
    _decryption_failed for the frontend to detect.
    """
    decrypt_model_content(model, user_id)


def get_daily_reports_by_week(
    db: Session, user_id: int, week_start: date
) -> list[models.DailyReport]:
    _, week_end = week_bounds(week_start)
    reports = (
        db.query(models.DailyReport)
        .filter(
            models.DailyReport.user_id == user_id,
            models.DailyReport.date >= week_start,
            models.DailyReport.date <= week_end,
        )
        .order_by(models.DailyReport.date)
        .all()
    )
    for r in reports:
        _decrypt_model_content(r, user_id)
    return reports


def get_daily_reports_range(
    db: Session, user_id: int, start_date: date, end_date: date
) -> list[models.DailyReport]:
    reports = (
        db.query(models.DailyReport)
        .filter(
            models.DailyReport.user_id == user_id,
            models.DailyReport.date >= start_date,
            models.DailyReport.date <= end_date,
        )
        .order_by(models.DailyReport.date)
        .all()
    )
    for r in reports:
        _decrypt_model_content(r, user_id)
    return reports


def upsert_daily_report(
    db: Session, user_id: int, report_date: date, content: str
) -> models.DailyReport:
    existing = get_daily_report(db, user_id, report_date)
    if existing:
        encrypt_model_content(existing, content, user_id)
        existing.updated_at = datetime.now(UTC)
        db.commit()
        db.refresh(existing)
        _decrypt_model_content(existing, user_id)
        return existing
    report = models.DailyReport(user_id=user_id, date=report_date, content="")
    encrypt_model_content(report, content, user_id)
    db.add(report)
    db.commit()
    db.refresh(report)
    _decrypt_model_content(report, user_id)
    return report


def delete_daily_report(db: Session, user_id: int, report_date: date) -> bool:
    report = get_daily_report(db, user_id, report_date)
    if report:
        db.delete(report)
        db.commit()
        return True
    return False


def get_daily_report_decrypted(db: Session, user_id: int, report_date: date) -> str | None:
    """Return decrypted content, or None if no report exists.

    Raises ContentDecryptionError when the report is encrypted but unreadable —
    callers (e.g. append mode) must not silently treat that as empty content.
    """
    report = get_daily_report(db, user_id, report_date)
    if not report:
        return None
    if report.content_encrypted:
        return decrypt_record_content(report, user_id)
    return report.content


# ─── Weekly Report ──────────────────────────────────────


def get_weekly_report(db: Session, user_id: int, week_start: date) -> models.WeeklyReport | None:
    report = (
        db.query(models.WeeklyReport)
        .filter(
            models.WeeklyReport.user_id == user_id,
            models.WeeklyReport.week_start == week_start,
        )
        .first()
    )
    if report:
        _decrypt_model_content(report, user_id)
    return report


def get_weekly_reports(db: Session, user_id: int, limit: int = 12) -> list[models.WeeklyReport]:
    reports = (
        db.query(models.WeeklyReport)
        .filter(models.WeeklyReport.user_id == user_id)
        .order_by(models.WeeklyReport.week_start.desc())
        .limit(limit)
        .all()
    )
    for r in reports:
        _decrypt_model_content(r, user_id)
    return reports


def save_weekly_report(
    db: Session,
    user_id: int,
    week_start: date,
    week_end: date,
    content: str,
    model_name: str,
) -> models.WeeklyReport:
    existing = get_weekly_report(db, user_id, week_start)
    return _save_encrypted_report(
        db,
        models.WeeklyReport,
        existing,
        user_id,
        content,
        model_name,
        week_start=week_start,
        week_end=week_end,
    )


# ─── Monthly Report ────────────────────────────────────


def get_monthly_report(
    db: Session, user_id: int, year: int, month: int
) -> models.MonthlyReport | None:
    report = (
        db.query(models.MonthlyReport)
        .filter(
            models.MonthlyReport.user_id == user_id,
            models.MonthlyReport.year == year,
            models.MonthlyReport.month == month,
        )
        .first()
    )
    if report:
        _decrypt_model_content(report, user_id)
    return report


def get_monthly_reports(db: Session, user_id: int, limit: int = 12) -> list[models.MonthlyReport]:
    reports = (
        db.query(models.MonthlyReport)
        .filter(models.MonthlyReport.user_id == user_id)
        .order_by(models.MonthlyReport.year.desc(), models.MonthlyReport.month.desc())
        .limit(limit)
        .all()
    )
    for r in reports:
        _decrypt_model_content(r, user_id)
    return reports


def save_monthly_report(
    db: Session,
    user_id: int,
    year: int,
    month: int,
    content: str,
    model_name: str,
) -> models.MonthlyReport:
    existing = get_monthly_report(db, user_id, year, month)
    return _save_encrypted_report(
        db,
        models.MonthlyReport,
        existing,
        user_id,
        content,
        model_name,
        year=year,
        month=month,
    )


# ─── App Config ─────────────────────────────────────────


def get_app_config(db: Session) -> models.AppConfig:
    config = db.query(models.AppConfig).filter(models.AppConfig.id == 1).first()
    if not config:
        config = models.AppConfig(id=1)
        db.add(config)
        db.commit()
        db.refresh(config)
    # Decrypt API key if it's encrypted. set_committed_value keeps the attribute
    # clean so a later commit in the same session never flushes plaintext back
    # into the api_key column.
    if config.api_key:
        set_committed_value(config, "api_key", decrypt_api_key(config.api_key))
    return config


def update_app_config(
    db: Session,
    llm_api_url: str | None = None,
    llm_model_name: str | None = None,
    api_key: str | None = None,
) -> models.AppConfig:
    config = db.query(models.AppConfig).filter(models.AppConfig.id == 1).first()
    if not config:
        config = models.AppConfig(id=1)
        db.add(config)
    if llm_api_url is not None:
        config.llm_api_url = llm_api_url
    if llm_model_name is not None:
        config.llm_model_name = llm_model_name
    # Callers pass None for "unchanged"; masked values are filtered in the router,
    # so a real key containing '*' can be stored.
    if api_key is not None:
        config.api_key = encrypt_api_key(api_key)
    config.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(config)
    # Return with decrypted API key (clean attribute — never flushed back).
    set_committed_value(
        config, "api_key", decrypt_api_key(config.api_key) if config.api_key else None
    )
    return config


# ─── Task ───────────────────────────────────────────────


def get_tasks(db: Session, user_id: int) -> list[models.Task]:
    """Get all tasks for a user, ordered by deadline (nulls last), then by created_at desc."""
    from sqlalchemy import nullslast

    tasks = (
        db.query(models.Task)
        .filter(models.Task.user_id == user_id)
        .order_by(
            nullslast(models.Task.deadline.asc()),
            models.Task.created_at.desc(),
        )
        .all()
    )
    for t in tasks:
        _decrypt_model_content(t, user_id)
    return tasks


def get_pending_tasks(db: Session, user_id: int) -> list[models.Task]:
    """Get incomplete tasks for a user."""
    from sqlalchemy import nullslast

    tasks = (
        db.query(models.Task)
        .filter(models.Task.user_id == user_id, models.Task.is_completed.is_(False))
        .order_by(
            nullslast(models.Task.deadline.asc()),
            models.Task.created_at.desc(),
        )
        .all()
    )
    for t in tasks:
        _decrypt_model_content(t, user_id)
    return tasks


def get_completed_tasks(
    db: Session, user_id: int, offset: int = 0, limit: int = 20
) -> list[models.Task]:
    """Get completed tasks for a user with pagination."""
    from sqlalchemy import nullslast

    tasks = (
        db.query(models.Task)
        .filter(models.Task.user_id == user_id, models.Task.is_completed)
        .order_by(
            nullslast(models.Task.deadline.desc()),
            models.Task.created_at.desc(),
        )
        .offset(offset)
        .limit(limit)
        .all()
    )
    for t in tasks:
        _decrypt_model_content(t, user_id)
    return tasks


def get_completed_tasks_count(db: Session, user_id: int) -> int:
    """Get total count of completed tasks for a user."""
    return (
        db.query(models.Task)
        .filter(models.Task.user_id == user_id, models.Task.is_completed)
        .count()
    )


def create_task(
    db: Session, user_id: int, content: str, deadline: date | None = None
) -> models.Task:
    # Validate deadline is not in the past
    if deadline and deadline < date.today():
        raise ValueError("截止日期不能早于今天")
    task = models.Task(user_id=user_id, content="", deadline=deadline)
    encrypt_model_content(task, content, user_id)
    db.add(task)
    db.commit()
    db.refresh(task)
    _decrypt_model_content(task, user_id)
    return task


def update_task(
    db: Session,
    user_id: int,
    task_id: int,
    content: str | None = None,
    deadline: date | None = None,
    is_completed: bool | None = None,
) -> models.Task | None:
    # Validate deadline is not in the past
    if deadline and deadline < date.today():
        raise ValueError("截止日期不能早于今天")
    task = (
        db.query(models.Task)
        .filter(models.Task.id == task_id, models.Task.user_id == user_id)
        .first()
    )
    if not task:
        return None
    if content is not None:
        encrypt_model_content(task, content, user_id)
    if deadline is not None:
        task.deadline = deadline
    if is_completed is not None:
        task.is_completed = is_completed
    task.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(task)
    _decrypt_model_content(task, user_id)
    return task


def delete_task(db: Session, user_id: int, task_id: int) -> bool:
    task = (
        db.query(models.Task)
        .filter(models.Task.id == task_id, models.Task.user_id == user_id)
        .first()
    )
    if task:
        db.delete(task)
        db.commit()
        return True
    return False


def get_task_decrypted(db: Session, user_id: int, task_id: int) -> str | None:
    """Return decrypted task content, or None if the task does not exist.

    Raises ContentDecryptionError when encrypted content is unreadable.
    """
    task = (
        db.query(models.Task)
        .filter(models.Task.id == task_id, models.Task.user_id == user_id)
        .first()
    )
    if not task:
        return None
    if task.content_encrypted:
        return decrypt_record_content(task, user_id)
    return task.content
