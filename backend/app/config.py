"""Application configuration using pydantic-settings."""

import base64
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
                'Generate one with: python -c "import secrets; print(secrets.token_urlsafe(64))"'
            )
        secret = secrets.token_urlsafe(64)
        print("⚠️  JWT_SECRET_KEY not set — using random key (tokens will be invalid on restart)")
    return secret


def _default_encryption_master_key() -> str:
    """Resolve the envelope-encryption master key (base64, 32 bytes decoded).

    Production: ENCRYPTION_MASTER_KEY is mandatory — refuse to start without it.
    Development: generate once and persist to <data dir>/.encryption_key (0600),
    so restarts keep existing ciphertext readable.
    """
    secret = os.getenv("ENCRYPTION_MASTER_KEY")
    if secret:
        return secret
    env = os.getenv("ENV", os.getenv("ENVIRONMENT", "development"))
    if env == "production":
        raise ValueError(
            "ENCRYPTION_MASTER_KEY environment variable is required in production. "
            'Generate one with: python -c "import base64, secrets; '
            'print(base64.b64encode(secrets.token_bytes(32)).decode())"'
        )
    db_url = os.getenv("DATABASE_URL", "sqlite:///./data/weekly_report.db")
    key_dir = os.path.dirname(db_url.replace("sqlite:///", "")) or "."
    os.makedirs(key_dir, exist_ok=True)
    key_file = os.path.join(key_dir, ".encryption_key")
    if os.path.exists(key_file):
        with open(key_file, encoding="ascii") as f:
            return f.read().strip()
    key = base64.b64encode(secrets.token_bytes(32)).decode()
    fd = os.open(key_file, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="ascii") as f:
        f.write(key + "\n")
    print(f"⚠️  ENCRYPTION_MASTER_KEY not set — generated dev key at {key_file} (keep it safe)")
    return key


class Settings(BaseSettings):
    # JWT
    jwt_secret_key: str = _default_jwt_secret()
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440  # 24 hours

    # Envelope encryption (master key → KEK → per-user DEK)
    encryption_master_key: str = _default_encryption_master_key()

    # Database
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./data/weekly_report.db")

    # Default LLM
    default_llm_api_url: str = "https://api.deepseek.com/v1/chat/completions"
    default_llm_model: str = "deepseek-v4-flash"

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
