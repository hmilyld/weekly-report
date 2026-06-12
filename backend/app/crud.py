"""CRUD operations."""

from datetime import UTC, date, datetime, timedelta

from sqlalchemy.orm import Session

from . import models

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


def get_daily_reports_by_week(
    db: Session, user_id: int, week_start: date
) -> list[models.DailyReport]:
    week_end = week_start + timedelta(days=6)
    return (
        db.query(models.DailyReport)
        .filter(
            models.DailyReport.user_id == user_id,
            models.DailyReport.date >= week_start,
            models.DailyReport.date <= week_end,
        )
        .order_by(models.DailyReport.date)
        .all()
    )


def get_daily_reports_range(
    db: Session, user_id: int, start_date: date, end_date: date
) -> list[models.DailyReport]:
    return (
        db.query(models.DailyReport)
        .filter(
            models.DailyReport.user_id == user_id,
            models.DailyReport.date >= start_date,
            models.DailyReport.date <= end_date,
        )
        .order_by(models.DailyReport.date)
        .all()
    )


def upsert_daily_report(
    db: Session, user_id: int, report_date: date, content: str
) -> models.DailyReport:
    existing = get_daily_report(db, user_id, report_date)
    if existing:
        existing.content = content
        from datetime import datetime

        existing.updated_at = datetime.now(UTC)
        db.commit()
        db.refresh(existing)
        return existing
    report = models.DailyReport(user_id=user_id, date=report_date, content=content)
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


def delete_daily_report(db: Session, user_id: int, report_date: date) -> bool:
    report = get_daily_report(db, user_id, report_date)
    if report:
        db.delete(report)
        db.commit()
        return True
    return False


# ─── Weekly Report ──────────────────────────────────────


def get_weekly_report(db: Session, user_id: int, week_start: date) -> models.WeeklyReport | None:
    return (
        db.query(models.WeeklyReport)
        .filter(
            models.WeeklyReport.user_id == user_id,
            models.WeeklyReport.week_start == week_start,
        )
        .first()
    )


def get_weekly_reports(db: Session, user_id: int, limit: int = 12) -> list[models.WeeklyReport]:
    return (
        db.query(models.WeeklyReport)
        .filter(models.WeeklyReport.user_id == user_id)
        .order_by(models.WeeklyReport.week_start.desc())
        .limit(limit)
        .all()
    )


def save_weekly_report(
    db: Session,
    user_id: int,
    week_start: date,
    week_end: date,
    content: str,
    model_name: str,
) -> models.WeeklyReport:
    existing = get_weekly_report(db, user_id, week_start)
    if existing:
        existing.content = content
        existing.model_name = model_name
        from datetime import datetime

        existing.generated_at = datetime.now(UTC)
        db.commit()
        db.refresh(existing)
        return existing
    report = models.WeeklyReport(
        user_id=user_id,
        week_start=week_start,
        week_end=week_end,
        content=content,
        model_name=model_name,
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


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

    return (
        db.query(models.Task)
        .filter(models.Task.user_id == user_id)
        .order_by(
            nullslast(models.Task.deadline.asc()),
            models.Task.created_at.desc(),
        )
        .all()
    )


def get_pending_tasks(db: Session, user_id: int) -> list[models.Task]:
    """Get incomplete tasks for a user."""
    from sqlalchemy import nullslast

    return (
        db.query(models.Task)
        .filter(models.Task.user_id == user_id, models.Task.is_completed.is_(False))
        .order_by(
            nullslast(models.Task.deadline.asc()),
            models.Task.created_at.desc(),
        )
        .all()
    )


def get_completed_tasks(
    db: Session, user_id: int, offset: int = 0, limit: int = 20
) -> list[models.Task]:
    """Get completed tasks for a user with pagination."""
    from sqlalchemy import nullslast

    return (
        db.query(models.Task)
        .filter(models.Task.user_id == user_id, models.Task.is_completed == True)
        .order_by(
            nullslast(models.Task.deadline.desc()),
            models.Task.created_at.desc(),
        )
        .offset(offset)
        .limit(limit)
        .all()
    )


def get_completed_tasks_count(db: Session, user_id: int) -> int:
    """Get total count of completed tasks for a user."""
    return (
        db.query(models.Task)
        .filter(models.Task.user_id == user_id, models.Task.is_completed == True)
        .count()
    )


def create_task(
    db: Session, user_id: int, content: str, deadline: date | None = None
) -> models.Task:
    # Validate deadline is not in the past
    if deadline and deadline < date.today():
        raise ValueError("截止日期不能早于今天")
    task = models.Task(user_id=user_id, content=content, deadline=deadline)
    db.add(task)
    db.commit()
    db.refresh(task)
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
        task.content = content
    if deadline is not None:
        task.deadline = deadline
    if is_completed is not None:
        task.is_completed = is_completed
    task.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(task)
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
