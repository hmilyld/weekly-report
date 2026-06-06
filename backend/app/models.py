"""SQLAlchemy ORM models."""

from datetime import UTC, datetime

from sqlalchemy import (
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from .database import Base


def _utcnow() -> datetime:
    return datetime.now(UTC)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    password_version = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=_utcnow, nullable=False)

    daily_reports = relationship("DailyReport", back_populates="user")
    weekly_reports = relationship("WeeklyReport", back_populates="user")


class DailyReport(Base):
    __tablename__ = "daily_reports"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    date = Column(Date, nullable=False)
    content = Column(Text, nullable=False, default="")
    created_at = Column(DateTime, default=_utcnow, nullable=False)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow, nullable=False)

    user = relationship("User", back_populates="daily_reports")

    __table_args__ = (UniqueConstraint("user_id", "date", name="uq_user_date"),)


class WeeklyReport(Base):
    __tablename__ = "weekly_reports"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    week_start = Column(Date, nullable=False)  # Monday
    week_end = Column(Date, nullable=False)  # Sunday
    content = Column(Text, nullable=False)
    model_name = Column(String(100), nullable=False, default="")
    generated_at = Column(DateTime, default=_utcnow, nullable=False)

    user = relationship("User", back_populates="weekly_reports")

    __table_args__ = (UniqueConstraint("user_id", "week_start", name="uq_user_week_start"),)


class AppConfig(Base):
    __tablename__ = "app_config"

    id = Column(Integer, primary_key=True, default=1)
    llm_api_url = Column(
        String(500), nullable=False, default="http://localhost:11434/v1/chat/completions"
    )
    llm_model_name = Column(String(100), nullable=False, default="llama2")
    api_key = Column(String(500), nullable=True, default="")
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow, nullable=False)
