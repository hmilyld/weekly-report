"""Weekly report router: query & generate weekly summaries."""

import logging
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from .. import crud
from ..auth import get_authenticated_user
from ..database import get_db
from ..date_range import week_bounds
from ..encryption_utils import (
    ContentDecryptionError,
    decrypt_daily_entries,
    update_report_content,
)
from ..llm_client import generate_weekly_report
from ..models import User, WeeklyReport
from ..schemas import (
    WeeklyReportItem,
    WeeklyReportListResponse,
    WeeklyReportResponse,
    WeeklyReportUpdate,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/weekly", tags=["weekly"])


@router.get("", response_model=WeeklyReportListResponse)
def list_weekly_reports(
    limit: int = Query(12, ge=1, le=52),
    user: User = Depends(get_authenticated_user),
    db: Session = Depends(get_db),
):
    """List the most recent weekly reports (newest first)."""
    reports = crud.get_weekly_reports(db, user.id, limit)
    return WeeklyReportListResponse(
        reports=reports,
        decryption_failed=any(getattr(report, "_decryption_failed", False) for report in reports),
    )


@router.get("/{week_start}", response_model=WeeklyReportItem)
def get_weekly_report(
    week_start: date,
    user: User = Depends(get_authenticated_user),
    db: Session = Depends(get_db),
):
    """Get the weekly report for a given week. Returns 404 if not generated yet."""
    report = crud.get_weekly_report(db, user.id, week_start)
    if not report:
        raise HTTPException(status_code=404, detail="Weekly report not found")
    return report


@router.post("/{week_start}", response_model=WeeklyReportResponse)
def generate_weekly_report_endpoint(
    week_start: date,
    force: bool = Query(True),
    user: User = Depends(get_authenticated_user),
    db: Session = Depends(get_db),
):
    """Generate (or regenerate) the weekly report for a given week.

    force=false returns the existing report without calling the LLM
    (`generated=false` in the response).
    """
    report, generated = _generate(db, user.id, week_start, force)
    response = WeeklyReportResponse.model_validate(report)
    return response.model_copy(update={"generated": generated})


@router.put("/{week_start}", response_model=WeeklyReportResponse)
def update_weekly_report(
    week_start: date,
    body: WeeklyReportUpdate,
    user: User = Depends(get_authenticated_user),
    db: Session = Depends(get_db),
):
    """Update the content of an existing weekly report."""
    report = crud.get_weekly_report(db, user.id, week_start)
    if not report:
        raise HTTPException(status_code=404, detail="Weekly report not found")
    update_report_content(db, report, body.content, user.id)
    return report


def _generate(
    db: Session, user_id: int, week_start: date, force: bool = True
) -> tuple[WeeklyReport, bool]:
    week_start, week_end = week_bounds(week_start)

    if not force:
        existing = crud.get_weekly_report(db, user_id, week_start)
        if existing:
            # Never hand back an empty string for an undecryptable report:
            # the client would mistake it for "no content".
            if getattr(existing, "_decryption_failed", False):
                raise ContentDecryptionError(
                    "Existing weekly report cannot be decrypted; refusing to return empty content"
                )
            return existing, False

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
    # save_weekly_report encrypts with the user's DEK and decrypts for return.
    report = crud.save_weekly_report(
        db, user_id, week_start, week_end, weekly_content, config.llm_model_name
    )
    return report, True
