"""Monthly report router: query & generate monthly summaries."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.orm import Session

from .. import crud
from ..auth import get_authenticated_user
from ..database import get_db
from ..date_range import month_bounds
from ..encryption_utils import decrypt_daily_entries, update_report_content
from ..llm_client import generate_monthly_report
from ..models import User
from ..schemas import (
    MonthlyReportItem,
    MonthlyReportListResponse,
    MonthlyReportResponse,
    MonthlyReportUpdate,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/monthly", tags=["monthly"])

YEAR_PARAM = Path(ge=1970, le=2100)
MONTH_PARAM = Path(ge=1, le=12)


@router.get("", response_model=MonthlyReportListResponse)
def list_monthly_reports(
    user: User = Depends(get_authenticated_user),
    db: Session = Depends(get_db),
):
    """List all saved monthly reports."""
    reports = crud.get_monthly_reports(db, user.id)
    return MonthlyReportListResponse(
        reports=reports,
        decryption_failed=any(getattr(report, "_decryption_failed", False) for report in reports),
    )


@router.get("/{year}/{month}", response_model=MonthlyReportItem)
def get_monthly_report(
    year: int = YEAR_PARAM,
    month: int = MONTH_PARAM,
    user: User = Depends(get_authenticated_user),
    db: Session = Depends(get_db),
):
    """Get the monthly report for a given month. Returns 404 if not generated yet."""
    report = crud.get_monthly_report(db, user.id, year, month)
    if not report:
        raise HTTPException(status_code=404, detail="Monthly report not found")
    return report


@router.post("/{year}/{month}", response_model=MonthlyReportResponse)
def generate_monthly_report_endpoint(
    year: int = YEAR_PARAM,
    month: int = MONTH_PARAM,
    user: User = Depends(get_authenticated_user),
    db: Session = Depends(get_db),
):
    """Generate (or regenerate) the monthly report for a given month."""
    return _generate(db, user.id, year, month)


@router.put("/{year}/{month}", response_model=MonthlyReportResponse)
def update_monthly_report(
    body: MonthlyReportUpdate,
    year: int = YEAR_PARAM,
    month: int = MONTH_PARAM,
    user: User = Depends(get_authenticated_user),
    db: Session = Depends(get_db),
):
    """Update the content of an existing monthly report."""
    report = crud.get_monthly_report(db, user.id, year, month)
    if not report:
        raise HTTPException(status_code=404, detail="Monthly report not found")
    update_report_content(db, report, body.content, user.id)
    return report


def _generate(db: Session, user_id: int, year: int, month: int) -> MonthlyReportResponse:
    month_start, month_end = month_bounds(year, month)

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
    # save_monthly_report encrypts with the user's DEK and decrypts for return.
    return crud.save_monthly_report(
        db, user_id, year, month, monthly_content, config.llm_model_name
    )
