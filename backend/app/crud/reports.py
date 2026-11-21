"""Daily / weekly / monthly report persistence (content is encrypted at rest)."""

from datetime import UTC, date, datetime

from sqlalchemy.orm import Session

from .. import models
from ..date_range import week_bounds
from ..encryption_utils import (
    decrypt_model_content,
    decrypt_record_content,
    encrypt_model_content,
)


def _save_encrypted_report(
    db: Session,
    model_class,
    existing,
    user_id: int,
    content: str,
    model_name: str,
    **kwargs,
):
    """Create or update an encrypted report of the given model class."""
    if existing:
        existing.model_name = model_name
        encrypt_model_content(existing, content, user_id)
        existing.generated_at = datetime.now(UTC)
        db.commit()
        db.refresh(existing)
        decrypt_model_content(existing, user_id)
        return existing

    report = model_class(user_id=user_id, model_name=model_name, **kwargs)
    encrypt_model_content(report, content, user_id)
    db.add(report)
    db.commit()
    db.refresh(report)
    decrypt_model_content(report, user_id)
    return report


# ─── Daily ──────────────────────────────────────────────


def get_daily_report(db: Session, user_id: int, report_date: date) -> models.DailyReport | None:
    return (
        db.query(models.DailyReport)
        .filter(models.DailyReport.user_id == user_id, models.DailyReport.date == report_date)
        .first()
    )


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
    for report in reports:
        decrypt_model_content(report, user_id)
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
    for report in reports:
        decrypt_model_content(report, user_id)
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
        decrypt_model_content(existing, user_id)
        return existing
    report = models.DailyReport(user_id=user_id, date=report_date, content="")
    encrypt_model_content(report, content, user_id)
    db.add(report)
    db.commit()
    db.refresh(report)
    decrypt_model_content(report, user_id)
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


# ─── Weekly ─────────────────────────────────────────────


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
        decrypt_model_content(report, user_id)
    return report


def get_weekly_reports(db: Session, user_id: int, limit: int = 12) -> list[models.WeeklyReport]:
    reports = (
        db.query(models.WeeklyReport)
        .filter(models.WeeklyReport.user_id == user_id)
        .order_by(models.WeeklyReport.week_start.desc())
        .limit(limit)
        .all()
    )
    for report in reports:
        decrypt_model_content(report, user_id)
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


# ─── Monthly ────────────────────────────────────────────


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
        decrypt_model_content(report, user_id)
    return report


def get_monthly_reports(db: Session, user_id: int, limit: int = 12) -> list[models.MonthlyReport]:
    reports = (
        db.query(models.MonthlyReport)
        .filter(models.MonthlyReport.user_id == user_id)
        .order_by(models.MonthlyReport.year.desc(), models.MonthlyReport.month.desc())
        .limit(limit)
        .all()
    )
    for report in reports:
        decrypt_model_content(report, user_id)
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
