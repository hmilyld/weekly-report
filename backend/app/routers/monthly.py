"""Monthly report router: query & generate monthly summaries."""

import calendar
import logging
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import crud
from ..auth import get_current_user
from ..database import get_db
from ..encryption_utils import decrypt_daily_entries, update_report_content
from ..llm_client import generate_monthly_report
from ..models import User
from ..schemas import MonthlyReportResponse, MonthlyReportUpdate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/monthly", tags=["monthly"])


def _get_month_bounds(year: int, month: int) -> tuple[date, date]:
    """Return (month_start, month_end) for the given year/month."""
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, 1), date(year, month, last_day)


@router.get("", response_model=list[MonthlyReportResponse])
def list_monthly_reports(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all saved monthly reports."""
    return crud.get_monthly_reports(db, user.id)


@router.get("/{year}/{month}", response_model=MonthlyReportResponse)
def get_monthly_report(
    year: int,
    month: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get the monthly report for a given month. Returns 404 if not generated yet."""
    report = crud.get_monthly_report(db, user.id, year, month)
    if not report:
        raise HTTPException(status_code=404, detail="Monthly report not found")
    return report


@router.post("/{year}/{month}", response_model=MonthlyReportResponse)
def generate_monthly_report_endpoint(
    year: int,
    month: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generate (or regenerate) the monthly report for a given month."""
    return _generate(db, user.id, year, month)


@router.put("/{year}/{month}", response_model=MonthlyReportResponse)
def update_monthly_report(
    year: int,
    month: int,
    body: MonthlyReportUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update the content of an existing monthly report."""
    report = crud.get_monthly_report(db, user.id, year, month)
    if not report:
        raise HTTPException(status_code=404, detail="Monthly report not found")
    update_report_content(db, report, body.content, user.id)
    return report


def _generate(db: Session, user_id: int, year: int, month: int) -> MonthlyReportResponse:
    month_start, month_end = _get_month_bounds(year, month)

    # Gather daily reports for the month
    dailies = crud.get_daily_reports_range(db, user_id, month_start, month_end)
    if not dailies:
        raise HTTPException(status_code=400, detail="No daily reports found for this month")

    daily_entries = decrypt_daily_entries(dailies, user_id)

    if not daily_entries:
        raise HTTPException(status_code=400, detail="All daily reports are empty for this month")

    try:
        monthly_content = generate_monthly_report(db, daily_entries)
    except RuntimeError as e:
        logger.error("LLM generation failed: %s", e)
        raise HTTPException(
            status_code=502, detail="LLM generation failed. Please check your configuration."
        ) from e

    config = crud.get_app_config(db)
    report = crud.save_monthly_report(
        db, user_id, year, month, monthly_content, config.llm_model_name
    )

    from ..encryption_utils import encrypt_model_content

    encrypt_model_content(report, monthly_content, user_id)
    db.commit()
    db.refresh(report)

    from ..crud import _decrypt_model_content

    _decrypt_model_content(report, user_id)
    return report
