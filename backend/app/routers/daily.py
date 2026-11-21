"""Daily report router: CRUD for daily work logs."""

from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import crud
from ..auth import get_authenticated_user
from ..database import get_db
from ..models import User
from ..schemas import (
    DailyReportCreate,
    DailyReportListResponse,
    DailyReportResponse,
    MessageResponse,
)

router = APIRouter(prefix="/api/v1/daily", tags=["daily"])

DEFAULT_START_DATE = date(2020, 1, 1)


def _list_response(reports: list) -> DailyReportListResponse:
    return DailyReportListResponse(
        reports=reports,
        decryption_failed=any(getattr(report, "_decryption_failed", False) for report in reports),
    )


@router.get("", response_model=DailyReportListResponse)
def list_daily_reports(
    start_date: date | None = None,
    end_date: date | None = None,
    user: User = Depends(get_authenticated_user),
    db: Session = Depends(get_db),
):
    """List daily reports. Optional date range filter (defaults to everything)."""
    start = start_date or DEFAULT_START_DATE
    end = end_date or (date.today() + timedelta(days=365))
    reports = crud.get_daily_reports_range(db, user.id, start, end)
    return _list_response(reports)


@router.get("/week/{week_start}", response_model=DailyReportListResponse)
def get_week_daily_reports(
    week_start: date,
    user: User = Depends(get_authenticated_user),
    db: Session = Depends(get_db),
):
    """Get daily reports for a specific week (Monday-Sunday)."""
    return _list_response(crud.get_daily_reports_by_week(db, user.id, week_start))


@router.post("", response_model=DailyReportResponse, status_code=status.HTTP_201_CREATED)
def create_or_update_daily_report(
    body: DailyReportCreate,
    user: User = Depends(get_authenticated_user),
    db: Session = Depends(get_db),
):
    """Create/update (upsert) a daily report. `date` defaults to today.

    `append=true` appends to the existing entry with a newline separator
    instead of overwriting it.
    """
    report_date = body.date or date.today()
    content = body.content
    if body.append:
        existing = crud.get_daily_report_decrypted(db, user.id, report_date) or ""
        content = existing + ("\n" if existing else "") + body.content
    return crud.upsert_daily_report(db, user.id, report_date, content)


@router.delete("/{report_date}", response_model=MessageResponse)
def delete_daily_report(
    report_date: date,
    user: User = Depends(get_authenticated_user),
    db: Session = Depends(get_db),
):
    """Delete a daily report by date."""
    deleted = crud.delete_daily_report(db, user.id, report_date)
    if not deleted:
        raise HTTPException(status_code=404, detail="No report found for this date")
    return {"message": "Deleted"}
