"""Pydantic schemas for request / response validation."""

from datetime import date, datetime

from pydantic import BaseModel, Field, field_validator

# ─── Auth ───────────────────────────────────────────────


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class PasswordChange(BaseModel):
    new_password: str = Field(min_length=8, max_length=100)


# ─── User Management ────────────────────────────────────


class UserCreate(BaseModel):
    username: str = Field(min_length=2, max_length=50)
    password: str = Field(min_length=8, max_length=100)
    role: str = Field(default="user", pattern=r"^(admin|user)$")


class UserResponse(BaseModel):
    id: int
    username: str
    role: str
    created_at: datetime

    model_config = {"from_attributes": True}


class UserListResponse(BaseModel):
    users: list[UserResponse]


class ChangeRoleRequest(BaseModel):
    role: str = Field(pattern=r"^(admin|user)$")


# ─── Daily Report ───────────────────────────────────────


class DailyReportCreate(BaseModel):
    date: date
    content: str = Field(default="", max_length=50000)


class DailyReportUpdate(BaseModel):
    content: str = Field(max_length=50000)


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


class WeeklyReportUpdate(BaseModel):
    content: str = Field(max_length=50000)


# ─── App Config ─────────────────────────────────────────


class AppConfigResponse(BaseModel):
    llm_api_url: str
    llm_model_name: str
    api_key: str | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class AppConfigUpdate(BaseModel):
    llm_api_url: str | None = Field(default=None, max_length=2000)
    llm_model_name: str | None = Field(default=None, max_length=200)
    api_key: str | None = Field(default=None, max_length=500)

    @field_validator("llm_api_url")
    @classmethod
    def validate_url(cls, v: str | None) -> str | None:
        if v is not None and v.strip():
            from urllib.parse import urlparse

            parsed = urlparse(v)
            if parsed.scheme not in ("http", "https"):
                raise ValueError("URL must start with http:// or https://")
            if not parsed.hostname:
                raise ValueError("URL must have a valid hostname")
        return v


# ─── Task ───────────────────────────────────────────────


class TaskCreate(BaseModel):
    content: str = Field(max_length=5000)
    deadline: date | None = None


class TaskUpdate(BaseModel):
    content: str | None = Field(default=None, max_length=5000)
    deadline: date | None = None
    is_completed: bool | None = None


class TaskResponse(BaseModel):
    id: int
    user_id: int
    content: str
    deadline: date | None
    is_completed: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
