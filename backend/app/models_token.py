"""API Token model for external integrations."""

import secrets
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from .database import Base


def generate_api_token() -> str:
    """Generate a secure random API token."""
    return secrets.token_hex(32)  # 64 chars


class ApiToken(Base):
    __tablename__ = "api_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(100), nullable=False, default="default")
    token = Column(String(64), unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC), nullable=False)
    last_used_at = Column(DateTime, nullable=True)

    user = relationship("User")
