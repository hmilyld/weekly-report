"""Pydantic schemas for request / response validation."""

from datetime import date, datetime

from pydantic import BaseModel, Field

# ─── Auth ───────────────────────────────────────────────


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class PasswordChange(BaseModel):
    new_password: str = Field(min_length=6)


# ─── Daily Report ───────────────────────────────────────


class DailyReportCreate(BaseModel):
    date: date
    content: str = ""


class DailyReportUpdate(BaseModel):
    content: str


class DailyReportResponse(BaseModel):
    id: int
    user_id: int
    date: date
    content: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ─── Weekly Report ──────────────────────────────────────


class WeeklyReportResponse(BaseModel):
    model_config = {"from_attributes": True, "protected_namespaces": ()}

    id: int
    user_id: int
    week_start: date
    week_end: date
    content: str
    model_name: str
    generated_at: datetime


class WeeklyReportGenerate(BaseModel):
    week_start: date
    force: bool = False  # Force regeneration even if exists


# ─── App Config ─────────────────────────────────────────


class AppConfigResponse(BaseModel):
    llm_api_url: str
    llm_model_name: str
    api_key: str | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class AppConfigUpdate(BaseModel):
    llm_api_url: str | None = None
    llm_model_name: str | None = None
    api_key: str | None = None
