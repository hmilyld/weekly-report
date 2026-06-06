"""CRUD operations."""

from datetime import UTC, date, timedelta

from sqlalchemy.orm import Session

from . import models

# ─── User ───────────────────────────────────────────────


def get_user_by_username(db: Session, username: str) -> models.User | None:
    return db.query(models.User).filter(models.User.username == username).first()


def create_user(db: Session, username: str, password_hash: str) -> models.User:
    user = models.User(username=username, password_hash=password_hash)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def change_password(db: Session, user: models.User, new_hash: str) -> None:
    user.password_hash = new_hash
    db.commit()


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
    if api_key is not None:
        config.api_key = api_key
    from datetime import datetime

    config.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(config)
    return config
