"""External API endpoints (API Token protected).

POST   /api/v1/external/daily          创建/更新日报
GET    /api/v1/external/docs            获取所有接口文档
GET    /api/v1/external/daily/current-week   获取当周日报
GET    /api/v1/external/weekly/recent  获取当周+上周周报
"""

from datetime import UTC, date, datetime, timedelta

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .. import crud
from ..database import get_db
from ..models import User
from ..models_token import ApiToken

router = APIRouter(prefix="/api/v1/external", tags=["external"])


class ExternalDailyReport(BaseModel):
    date: str | None = None  # yyyy-mm-dd, defaults to today
    content: str
    append: bool = False  # False = overwrite, True = append


def get_user_by_api_token(
    x_api_token: str = Header(..., alias="X-API-Token"),
    db: Session = Depends(get_db),
) -> User:
    """Authenticate user via API token."""
    api_token = db.query(ApiToken).filter(ApiToken.token == x_api_token).first()
    if not api_token:
        raise HTTPException(status_code=401, detail="Invalid API token")

    # Update last_used_at
    api_token.last_used_at = datetime.now(UTC)
    db.commit()

    user = db.query(User).filter(User.id == api_token.user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="Token owner not found")
    return user


@router.post("/daily")
def create_daily_report(
    body: ExternalDailyReport,
    user: User = Depends(get_user_by_api_token),
    db: Session = Depends(get_db),
):
    """Create or update a daily report using API token."""
    # Parse date
    if body.date:
        try:
            report_date = date.fromisoformat(body.date)
        except ValueError as err:
            raise HTTPException(
                status_code=400, detail="Invalid date format, use yyyy-mm-dd"
            ) from err
    else:
        report_date = date.today()

    # Get existing report
    existing = crud.get_daily_report(db, user.id, report_date)

    if body.append and existing:
        # Append mode
        sep = "\n" if existing.content else ""
        new_content = existing.content + sep + body.content
    else:
        # Overwrite mode
        new_content = body.content

    report = crud.upsert_daily_report(db, user.id, report_date, new_content)
    return {
        "message": "ok",
        "date": str(report.date),
        "mode": "append" if body.append else "overwrite",
        "content_length": len(report.content),
    }


# ─── Helpers ─────────────────────────────────────────────


def _get_monday(d: date) -> date:
    """Return Monday of the week containing date `d`."""
    return d - timedelta(days=d.weekday())


# ─── Endpoint 1: API docs ───────────────────────────────


@router.get("/docs")
def get_api_docs(user: User = Depends(get_user_by_api_token)):
    """返回所有可用的 API 接口及其参数说明，供 AI 识别和调用。"""
    return {
        "apis": [
            {
                "method": "POST",
                "path": "/api/v1/external/daily",
                "summary": "创建或更新日报",
                "params": {
                    "content": {"type": "string", "required": True, "description": "日报内容"},
                    "date": {
                        "type": "string",
                        "required": False,
                        "description": "日期，格式 yyyy-mm-dd，默认当天",
                    },
                    "append": {
                        "type": "bool",
                        "required": False,
                        "description": "false=覆盖（默认），true=追加到已有内容后",
                    },
                },
            },
            {
                "method": "GET",
                "path": "/api/v1/external/daily/current-week",
                "summary": "获取当周已填写的日报",
                "description": "返回当前周（周一至周日）每天的日报内容；未填写的日期返回空字符串。",
                "params": {},
            },
            {
                "method": "GET",
                "path": "/api/v1/external/weekly/recent",
                "summary": "获取当周和上周的周报",
                "description": "返回当周与上一周的周报内容；未生成则返回 null。",
                "params": {},
            },
            {
                "method": "GET",
                "path": "/api/v1/external/docs",
                "summary": "获取所有接口文档",
                "description": "返回此列表，供 AI 自动发现可用接口。",
                "params": {},
            },
        ]
    }


# ─── Endpoint 2: Current week daily reports ──────────────


@router.get("/daily/current-week")
def get_current_week_daily(
    user: User = Depends(get_user_by_api_token),
    db: Session = Depends(get_db),
):
    """返回当周（周一~周日）的日报列表。

    每条包含 date 和 content。
    未填写日报的日期不包含在列表中（前端可据此判断「无」）。
    """
    monday = _get_monday(date.today())
    reports = crud.get_daily_reports_by_week(db, user.id, monday)

    if not reports:
        return {"week_start": str(monday), "reports": [], "message": "本周暂无日报"}

    return {
        "week_start": str(monday),
        "reports": [{"date": str(r.date), "content": r.content} for r in reports],
    }


# ─── Endpoint 3: Current + last week weekly reports ──────


@router.get("/weekly/recent")
def get_recent_weekly_reports(
    user: User = Depends(get_user_by_api_token),
    db: Session = Depends(get_db),
):
    """返回当周和上一周的周报。

    未生成周报的周次返回 null。
    """
    today = date.today()
    this_monday = _get_monday(today)
    last_monday = this_monday - timedelta(days=7)

    this_week = crud.get_weekly_report(db, user.id, this_monday)
    last_week = crud.get_weekly_report(db, user.id, last_monday)

    def _serialize(report):
        if report is None:
            return None
        return {
            "week_start": str(report.week_start),
            "week_end": str(report.week_end),
            "content": report.content,
            "model_name": report.model_name,
            "generated_at": report.generated_at.isoformat(),
        }

    return {
        "this_week": _serialize(this_week),
        "last_week": _serialize(last_week),
    }
