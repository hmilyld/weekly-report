"""Application configuration using pydantic-settings."""

import os

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # JWT
    jwt_secret_key: str = os.getenv("JWT_SECRET_KEY", "dev-secret-change-in-production")
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
