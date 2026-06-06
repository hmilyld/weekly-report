"""Daily report router: CRUD for daily work logs."""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import crud
from ..auth import get_current_user
from ..database import get_db
from ..models import User
from ..schemas import DailyReportCreate, DailyReportResponse

router = APIRouter(prefix="/api/v1/daily", tags=["daily"])


@router.get("", response_model=list[DailyReportResponse])
def list_daily_reports(
    start_date: date | None = None,
    end_date: date | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List daily reports. Optional date range filter."""
    if start_date and end_date:
        return crud.get_daily_reports_range(db, user.id, start_date, end_date)
    # Default: return all
    from datetime import timedelta

    if not start_date:
        start_date = date(2020, 1, 1)
    if not end_date:
        end_date = date.today() + timedelta(days=365)
    return crud.get_daily_reports_range(db, user.id, start_date, end_date)


@router.get("/week/{week_start}", response_model=list[DailyReportResponse])
def get_week_daily_reports(
    week_start: date,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get daily reports for a specific week (Monday-Sunday)."""
    return crud.get_daily_reports_by_week(db, user.id, week_start)


@router.post("", response_model=DailyReportResponse, status_code=status.HTTP_201_CREATED)
def create_or_update_daily_report(
    body: DailyReportCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create or update (upsert) a daily report."""
    return crud.upsert_daily_report(db, user.id, body.date, body.content)


@router.delete("/{report_date}")
def delete_daily_report(
    report_date: date,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a daily report by date."""
    deleted = crud.delete_daily_report(db, user.id, report_date)
    if not deleted:
        raise HTTPException(status_code=404, detail="No report found for this date")
    return {"message": "Deleted"}
