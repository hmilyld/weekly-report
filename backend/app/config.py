"""Application configuration using pydantic-settings.

Secrets are resolved AFTER pydantic-settings has read ``.env``. Resolving them as
static field defaults would run before the env file is loaded, which silently
defeats the production guards and writes a dev key file even when a real key is
configured.
"""

import base64
import binascii
import os
import secrets
from pathlib import Path

from pydantic import AliasChoices, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

MIN_JWT_SECRET_BYTES = 32
MASTER_KEY_BYTES = 32

# Values shipped in docs/examples must never be accepted as a real signing key.
_PLACEHOLDER_JWT_SECRETS = {
    "your-super-secret-key-change-this",
    "your-secret-key-here",
    "change-this",
    "changeme",
    "change-me",
    "secret",
    "jwt-secret",
}

_DEV_KEY_FILENAME = ".encryption_key"


def _generate_jwt_secret() -> str:
    return secrets.token_urlsafe(64)


def _generate_master_key() -> str:
    return base64.b64encode(secrets.token_bytes(MASTER_KEY_BYTES)).decode()


def validate_master_key(value: str) -> None:
    """Reject master keys that are not base64 of exactly 32 bytes."""
    try:
        raw = base64.b64decode(value, validate=True)
    except (binascii.Error, ValueError) as err:
        raise ValueError("ENCRYPTION_MASTER_KEY is not valid base64") from err
    if len(raw) != MASTER_KEY_BYTES:
        raise ValueError(
            f"ENCRYPTION_MASTER_KEY must decode to exactly {MASTER_KEY_BYTES} bytes (got {len(raw)})"
        )


def sqlite_data_dir(database_url: str) -> str:
    """Directory that holds the SQLite file (``.`` for non-SQLite URLs)."""
    prefix = "sqlite:///"
    if not database_url.startswith(prefix):
        return "."
    return os.path.dirname(database_url[len(prefix) :]) or "."


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # production → mandatory secrets + HSTS; anything else is development.
    environment: str = Field(
        default="development",
        validation_alias=AliasChoices("ENV", "ENVIRONMENT"),
    )

    # JWT
    jwt_secret_key: str = Field(default="", validation_alias=AliasChoices("JWT_SECRET_KEY"))
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440  # 24 hours

    # Envelope encryption (master key → KEK → per-user DEK)
    encryption_master_key: str = Field(
        default="", validation_alias=AliasChoices("ENCRYPTION_MASTER_KEY")
    )

    # Database
    database_url: str = Field(
        default="sqlite:///./data/weekly_report.db",
        validation_alias=AliasChoices("DATABASE_URL"),
    )

    # Default LLM
    default_llm_api_url: str = "https://api.deepseek.com/v1/chat/completions"
    default_llm_model: str = "deepseek-v4-flash"

    @property
    def is_production(self) -> bool:
        return self.environment.strip().lower() == "production"

    @property
    def dev_key_path(self) -> Path:
        """Location of the development master-key file (never used in production)."""
        return Path(sqlite_data_dir(self.database_url)) / _DEV_KEY_FILENAME

    @model_validator(mode="after")
    def _resolve_secrets(self) -> "Settings":
        self.jwt_secret_key = self._resolve_jwt_secret()
        self.encryption_master_key = self._resolve_master_key()
        return self

    def _resolve_jwt_secret(self) -> str:
        secret = self.jwt_secret_key.strip()
        if secret:
            if secret.lower() in _PLACEHOLDER_JWT_SECRETS:
                raise ValueError(
                    "JWT_SECRET_KEY is still the placeholder value from .env.example. "
                    'Generate one with: python -c "import secrets; print(secrets.token_urlsafe(64))"'
                )
            if len(secret.encode()) < MIN_JWT_SECRET_BYTES:
                raise ValueError(
                    f"JWT_SECRET_KEY must be at least {MIN_JWT_SECRET_BYTES} bytes. "
                    'Generate one with: python -c "import secrets; print(secrets.token_urlsafe(64))"'
                )
            return secret
        if self.is_production:
            raise ValueError(
                "JWT_SECRET_KEY environment variable is required in production. "
                'Generate one with: python -c "import secrets; print(secrets.token_urlsafe(64))"'
            )
        print("⚠️  JWT_SECRET_KEY not set — using random key (tokens will be invalid on restart)")
        return _generate_jwt_secret()

    def _resolve_master_key(self) -> str:
        key = self.encryption_master_key.strip()
        if key:
            validate_master_key(key)
            return key
        if self.is_production:
            raise ValueError(
                "ENCRYPTION_MASTER_KEY environment variable is required in production. "
                'Generate one with: python -c "import base64, secrets; '
                'print(base64.b64encode(secrets.token_bytes(32)).decode())"'
            )
        return self._load_or_create_dev_key()

    def _load_or_create_dev_key(self) -> str:
        """Development only: persist one generated key so ciphertext stays readable."""
        key_path = self.dev_key_path
        if key_path.exists():
            existing = key_path.read_text(encoding="ascii").strip()
            validate_master_key(existing)
            return existing
        key = _generate_master_key()
        key_path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(key_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="ascii") as f:
            f.write(key + "\n")
        print(f"⚠️  ENCRYPTION_MASTER_KEY not set — generated dev key at {key_path} (keep it safe)")
        return key


settings = Settings()
