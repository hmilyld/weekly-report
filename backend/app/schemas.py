"""Pydantic schemas for request / response validation."""

import datetime as dt
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

# ─── Auth ───────────────────────────────────────────────


class LoginRequest(BaseModel):
    username: str = Field(max_length=50)
    password: str = Field(max_length=100)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class PasswordChange(BaseModel):
    old_password: str = Field(min_length=1, max_length=100)
    new_password: str = Field(min_length=8, max_length=100)


class SetupRequest(BaseModel):
    username: str = Field(min_length=2, max_length=50)
    password: str = Field(min_length=8, max_length=100)


class SetupStatus(BaseModel):
    needs_setup: bool


# ─── API Tokens ─────────────────────────────────────────


class ApiTokenCreate(BaseModel):
    name: str = Field(default="default", max_length=100)


class ApiTokenResponse(BaseModel):
    id: int
    name: str
    # Only returned once, on creation.
    token: str | None = None
    created_at: datetime
    last_used_at: datetime | None = None

    model_config = {"from_attributes": True}


class ApiTokenCreatedResponse(BaseModel):
    id: int
    name: str
    token: str
    created_at: datetime


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
    last_login_at: datetime | None = None

    model_config = {"from_attributes": True}


class UserListResponse(BaseModel):
    users: list[UserResponse]


class ChangeRoleRequest(BaseModel):
    role: str = Field(pattern=r"^(admin|user)$")


# ─── Shared response base ───────────────────────────────


class OrmModel(BaseModel):
    """Base for responses built from an ORM row.

    ``decryption_failed`` is serialised as ``_decryption_failed`` because that is
    the documented wire contract (see docs/android-api.md): a true value means
    the ciphertext could not be read, so an empty string is not "no content".
    """

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        protected_namespaces=(),
    )

    decryption_failed: bool = Field(default=False, alias="_decryption_failed")


class ListResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    decryption_failed: bool = Field(default=False, alias="_decryption_failed")


# ─── Daily Report ───────────────────────────────────────


class DailyReportCreate(BaseModel):
    # date omitted → today (token/automation clients omit it).
    # dt.date: the field name `date` shadows the imported type inside the class.
    date: dt.date | None = None
    content: str = Field(default="", max_length=50000)
    # append=True appends to the existing entry with a newline separator
    append: bool = False


class DailyReportResponse(OrmModel):
    id: int
    user_id: int
    date: date
    content: str
    created_at: datetime
    updated_at: datetime


class DailyReportItem(OrmModel):
    id: int
    date: date
    content: str
    created_at: datetime
    updated_at: datetime


class DailyReportListResponse(ListResponse):
    reports: list[DailyReportItem]


# ─── Weekly Report ──────────────────────────────────────


class WeeklyReportItem(OrmModel):
    id: int
    user_id: int
    week_start: date
    week_end: date
    content: str
    model_name: str
    generated_at: datetime


class WeeklyReportResponse(WeeklyReportItem):
    # False when an existing report was returned without calling the LLM
    generated: bool = True


class WeeklyReportUpdate(BaseModel):
    content: str = Field(max_length=50000)


class WeeklyReportListResponse(ListResponse):
    reports: list[WeeklyReportItem]


# ─── Monthly Report ────────────────────────────────────


class MonthlyReportItem(OrmModel):
    id: int
    user_id: int
    year: int
    month: int
    content: str
    model_name: str
    generated_at: datetime


class MonthlyReportResponse(MonthlyReportItem):
    pass


class MonthlyReportUpdate(BaseModel):
    content: str = Field(max_length=50000)


class MonthlyReportListResponse(ListResponse):
    reports: list[MonthlyReportItem]


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
    content: str = Field(min_length=1, max_length=5000)
    deadline: date | None = None


class TaskUpdate(BaseModel):
    content: str | None = Field(default=None, max_length=5000)
    deadline: date | None = None
    is_completed: bool | None = None


class TaskResponse(OrmModel):
    id: int
    user_id: int
    content: str
    deadline: date | None
    is_completed: bool
    created_at: datetime
    updated_at: datetime


class TaskListResponse(ListResponse):
    tasks: list[TaskResponse]


class CompletedTaskListResponse(TaskListResponse):
    total: int
    offset: int
    limit: int
