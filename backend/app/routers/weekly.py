"""Weekly report router: query & generate weekly summaries."""

import logging
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import crud
from ..auth import get_current_user
from ..database import get_db
from ..encryption_utils import decrypt_daily_entries, update_report_content
from ..llm_client import generate_weekly_report
from ..models import User
from ..schemas import WeeklyReportResponse, WeeklyReportUpdate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/weekly", tags=["weekly"])


def _get_week_bounds(week_start: date) -> tuple[date, date]:
    """Return (week_start, week_end) where week_end = week_start + 6 days."""
    return week_start, week_start + timedelta(days=6)


@router.get("")
def list_weekly_reports(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all saved weekly reports."""
    reports = crud.get_weekly_reports(db, user.id)
    has_decryption_failed = any(getattr(r, '_decryption_failed', False) for r in reports)
    return {
        "reports": [
            {
                "id": r.id,
                "week_start": str(r.week_start),
                "week_end": str(r.week_end),
                "content": r.content,
                "model_name": r.model_name,
                "generated_at": r.generated_at.isoformat(),
                "_decryption_failed": getattr(r, '_decryption_failed', False),
            }
            for r in reports
        ],
        "_decryption_failed": has_decryption_failed,
    }


@router.get("/{week_start}")
def get_weekly_report(
    week_start: date,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get the weekly report for a given week. Returns 404 if not generated yet."""
    report = crud.get_weekly_report(db, user.id, week_start)
    if not report:
        raise HTTPException(status_code=404, detail="Weekly report not found")
    return {
        "id": report.id,
        "week_start": str(report.week_start),
        "week_end": str(report.week_end),
        "content": report.content,
        "model_name": report.model_name,
        "generated_at": report.generated_at.isoformat(),
        "_decryption_failed": getattr(report, '_decryption_failed', False),
    }


@router.post("/{week_start}", response_model=WeeklyReportResponse)
def generate_weekly_report_endpoint(
    week_start: date,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generate (or regenerate) the weekly report for a given week."""
    return _generate(db, user.id, week_start)


@router.put("/{week_start}", response_model=WeeklyReportResponse)
def update_weekly_report(
    week_start: date,
    body: WeeklyReportUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update the content of an existing weekly report."""
    report = crud.get_weekly_report(db, user.id, week_start)
    if not report:
        raise HTTPException(status_code=404, detail="Weekly report not found")
    update_report_content(db, report, body.content, user.id)
    return report


def _generate(db: Session, user_id: int, week_start: date) -> WeeklyReportResponse:
    week_start, week_end = _get_week_bounds(week_start)

    # Gather daily reports
    dailies = crud.get_daily_reports_by_week(db, user_id, week_start)
    if not dailies:
        raise HTTPException(status_code=400, detail="No daily reports found for this week")

    daily_entries = decrypt_daily_entries(dailies, user_id)

    if not daily_entries:
        raise HTTPException(status_code=400, detail="All daily reports are empty for this week")

    try:
        weekly_content = generate_weekly_report(db, daily_entries)
    except RuntimeError as e:
        logger.error("LLM generation failed: %s", e)
        raise HTTPException(
            status_code=502, detail="LLM generation failed. Please check your configuration."
        ) from e

    config = crud.get_app_config(db)
    report = crud.save_weekly_report(
        db, user_id, week_start, week_end, weekly_content, config.llm_model_name
    )

    from ..encryption_utils import encrypt_model_content

    encrypt_model_content(report, weekly_content, user_id)
    db.commit()
    db.refresh(report)

    from ..crud import _decrypt_model_content

    _decrypt_model_content(report, user_id)
    return report
