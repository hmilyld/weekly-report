"""Application configuration using pydantic-settings."""

import os
import secrets

from pydantic_settings import BaseSettings


def _default_jwt_secret() -> str:
    secret = os.getenv("JWT_SECRET_KEY")
    if not secret:
        env = os.getenv("ENV", os.getenv("ENVIRONMENT", "development"))
        if env == "production":
            raise ValueError(
                "JWT_SECRET_KEY environment variable is required in production. "
                "Generate one with: python -c \"import secrets; print(secrets.token_urlsafe(64))\""
            )
        secret = secrets.token_urlsafe(64)
        print(f"⚠️  JWT_SECRET_KEY not set — using random key (tokens will be invalid on restart)")
    return secret


class Settings(BaseSettings):
    # JWT
    jwt_secret_key: str = _default_jwt_secret()
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440  # 24 hours

    # Database
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./data/weekly_report.db")

    # Default LLM
    default_llm_api_url: str = "https://api.deepseek.com/v1/chat/completions"
    default_llm_model: str = "deepseek-v4-flash"

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
