"""CRUD operations."""

from datetime import UTC, date, datetime, timedelta

from sqlalchemy.orm import Session

from . import models
from .crypto import decrypt_content, encrypt_content, generate_salt
from .key_cache import key_cache


def _encrypt_and_set_content(model, content: str, user_id: int) -> None:
    """Encrypt content and set all encryption fields on a model instance."""
    key = key_cache.get(user_id)
    if key:
        salt = generate_salt()
        encrypted = encrypt_content(content, key)
        model.content = ""
        model.content_encrypted = encrypted["ciphertext"]
        model.content_salt = salt.hex()
        model.content_nonce = encrypted["nonce"]
        model.content_tag = encrypted["tag"]
        model.content_version = 1
    else:
        model.content = content
        model.content_encrypted = None
        model.content_salt = None
        model.content_nonce = None
        model.content_tag = None
        model.content_version = None


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
    """Decrypt content_encrypted field back into content on a model instance."""
    if not model.content_encrypted:
        return
    key = key_cache.get(user_id)
    if not key:
        return
    try:
        model.content = decrypt_content(
            {
                "ciphertext": model.content_encrypted,
                "nonce": model.content_nonce or "",
                "tag": model.content_tag or "",
            },
            key,
        )
    except Exception:
        pass


def get_daily_reports_by_week(
    db: Session, user_id: int, week_start: date
) -> list[models.DailyReport]:
    week_end = week_start + timedelta(days=6)
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
    key = key_cache.get(user_id)
    existing = get_daily_report(db, user_id, report_date)
    if existing:
        existing.content = content
        if key:
            salt = generate_salt()
            encrypted = encrypt_content(content, key)
            existing.content = ""
            existing.content_encrypted = encrypted["ciphertext"]
            existing.content_salt = salt.hex()
            existing.content_nonce = encrypted["nonce"]
            existing.content_tag = encrypted["tag"]
            existing.content_version = 1
        else:
            existing.content_encrypted = None
            existing.content_salt = None
            existing.content_nonce = None
            existing.content_tag = None
            existing.content_version = None
        from datetime import datetime

        existing.updated_at = datetime.now(UTC)
        db.commit()
        db.refresh(existing)
        _decrypt_model_content(existing, user_id)
        return existing
    if key:
        salt = generate_salt()
        encrypted = encrypt_content(content, key)
        report = models.DailyReport(
            user_id=user_id,
            date=report_date,
            content="",
            content_encrypted=encrypted["ciphertext"],
            content_salt=salt.hex(),
            content_nonce=encrypted["nonce"],
            content_tag=encrypted["tag"],
            content_version=1,
        )
    else:
        report = models.DailyReport(user_id=user_id, date=report_date, content=content)
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
    report = get_daily_report(db, user_id, report_date)
    if not report:
        return None
    if report.content_encrypted:
        key = key_cache.get(user_id)
        if not key:
            return None
        return decrypt_content(
            {
                "ciphertext": report.content_encrypted,
                "nonce": report.content_nonce or "",
                "tag": report.content_tag or "",
            },
            key,
        )
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
    return config


def update_app_config(
    db: Session,
    llm_api_url: str | None = None,
    llm_model_name: str | None = None,
    api_key: str | None = None,
) -> models.AppConfig:
    config = get_app_config(db)
    if llm_api_url is not None:
        config.llm_api_url = llm_api_url
    if llm_model_name is not None:
        config.llm_model_name = llm_model_name
    # Skip masked keys (contain *) — only update with real keys
    if api_key is not None and "*" not in api_key:
        config.api_key = api_key
    from datetime import datetime

    config.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(config)
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
    key = key_cache.get(user_id)
    if key:
        salt = generate_salt()
        encrypted = encrypt_content(content, key)
        task = models.Task(
            user_id=user_id,
            content="",
            content_encrypted=encrypted["ciphertext"],
            content_salt=salt.hex(),
            content_nonce=encrypted["nonce"],
            content_tag=encrypted["tag"],
            content_version=1,
            deadline=deadline,
        )
    else:
        task = models.Task(user_id=user_id, content=content, deadline=deadline)
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
        key = key_cache.get(user_id)
        if key:
            salt = generate_salt()
            encrypted = encrypt_content(content, key)
            task.content = ""
            task.content_encrypted = encrypted["ciphertext"]
            task.content_salt = salt.hex()
            task.content_nonce = encrypted["nonce"]
            task.content_tag = encrypted["tag"]
            task.content_version = 1
        else:
            task.content = content
            task.content_encrypted = None
            task.content_salt = None
            task.content_nonce = None
            task.content_tag = None
            task.content_version = None
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
    task = (
        db.query(models.Task)
        .filter(models.Task.id == task_id, models.Task.user_id == user_id)
        .first()
    )
    if not task:
        return None
    if task.content_encrypted:
        key = key_cache.get(user_id)
        if not key:
            return None
        return decrypt_content(
            {
                "ciphertext": task.content_encrypted,
                "nonce": task.content_nonce or "",
                "tag": task.content_tag or "",
            },
            key,
        )
    return task.content
