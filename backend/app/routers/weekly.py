"""Weekly report router: query & generate weekly summaries."""

from datetime import UTC, date, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .. import crud
from ..auth import get_current_user
from ..database import get_db
from ..llm_client import generate_weekly_report
from ..models import User
from ..schemas import WeeklyReportResponse

router = APIRouter(prefix="/api/v1/weekly", tags=["weekly"])


def _get_week_bounds(week_start: date) -> tuple[date, date]:
    """Return (week_start, week_end) where week_end = week_start + 6 days."""
    return week_start, week_start + timedelta(days=6)


class WeeklyReportUpdate(BaseModel):
    content: str


@router.get("", response_model=list[WeeklyReportResponse])
def list_weekly_reports(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all saved weekly reports."""
    return crud.get_weekly_reports(db, user.id)


@router.get("/{week_start}", response_model=WeeklyReportResponse)
def get_weekly_report(
    week_start: date,
    user: User = Depends(get_current_user),
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
    report.content = body.content
    from datetime import datetime

    report.generated_at = datetime.now(UTC)
    db.commit()
    db.refresh(report)
    return report


def _generate(db: Session, user_id: int, week_start: date) -> WeeklyReportResponse:
    week_start, week_end = _get_week_bounds(week_start)

    # Gather daily reports
    dailies = crud.get_daily_reports_by_week(db, user_id, week_start)
    if not dailies:
        raise HTTPException(status_code=400, detail="No daily reports found for this week")

    daily_entries = [(str(d.date), d.content) for d in dailies if d.content.strip()]
    if not daily_entries:
        raise HTTPException(status_code=400, detail="All daily reports are empty for this week")

    try:
        content = generate_weekly_report(db, daily_entries)
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=f"LLM generation failed: {e!s}") from e

    config = crud.get_app_config(db)
    report = crud.save_weekly_report(
        db, user_id, week_start, week_end, content, config.llm_model_name
    )
    return report
