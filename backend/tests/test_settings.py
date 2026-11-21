"""Settings guards: .env must be honored, weak/placeholder secrets rejected."""

import base64

import pytest
from pydantic import ValidationError

from app.config import Settings, validate_master_key

VALID_MASTER_KEY = base64.b64encode(bytes(range(32))).decode()
VALID_JWT_SECRET = "j" * 48


def _settings(monkeypatch, tmp_path, **env):
    """Build a Settings instance isolated from the repo's .env and CWD."""
    monkeypatch.chdir(tmp_path)
    for name in ("ENV", "ENVIRONMENT", "JWT_SECRET_KEY", "ENCRYPTION_MASTER_KEY", "DATABASE_URL"):
        monkeypatch.delenv(name, raising=False)
    for name, value in env.items():
        monkeypatch.setenv(name, value)
    return Settings(_env_file=None)


def test_production_requires_jwt_secret(monkeypatch, tmp_path):
    with pytest.raises(ValidationError, match="JWT_SECRET_KEY"):
        _settings(monkeypatch, tmp_path, ENV="production", ENCRYPTION_MASTER_KEY=VALID_MASTER_KEY)


def test_production_requires_master_key(monkeypatch, tmp_path):
    with pytest.raises(ValidationError, match="ENCRYPTION_MASTER_KEY"):
        _settings(monkeypatch, tmp_path, ENV="production", JWT_SECRET_KEY=VALID_JWT_SECRET)


def test_env_file_production_flag_is_honored(monkeypatch, tmp_path):
    """Regression: ENV=production in .env must trigger the guards, not the dev fallback."""
    monkeypatch.chdir(tmp_path)
    for name in ("ENV", "ENVIRONMENT", "JWT_SECRET_KEY", "ENCRYPTION_MASTER_KEY", "DATABASE_URL"):
        monkeypatch.delenv(name, raising=False)
    (tmp_path / ".env").write_text("ENV=production\n", encoding="utf-8")

    with pytest.raises(ValidationError, match="JWT_SECRET_KEY"):
        Settings()


def test_placeholder_jwt_secret_rejected(monkeypatch, tmp_path):
    with pytest.raises(ValidationError, match="placeholder"):
        _settings(
            monkeypatch,
            tmp_path,
            JWT_SECRET_KEY="your-super-secret-key-change-this",
            ENCRYPTION_MASTER_KEY=VALID_MASTER_KEY,
        )


def test_short_jwt_secret_rejected(monkeypatch, tmp_path):
    with pytest.raises(ValidationError, match="at least"):
        _settings(
            monkeypatch, tmp_path, JWT_SECRET_KEY="short", ENCRYPTION_MASTER_KEY=VALID_MASTER_KEY
        )


def test_invalid_master_key_rejected(monkeypatch, tmp_path):
    with pytest.raises(ValidationError, match="base64"):
        _settings(
            monkeypatch,
            tmp_path,
            JWT_SECRET_KEY=VALID_JWT_SECRET,
            ENCRYPTION_MASTER_KEY="not-base64",
        )


def test_dev_generates_and_reuses_key_file(monkeypatch, tmp_path):
    first = _settings(monkeypatch, tmp_path, DATABASE_URL="sqlite:///./data/app.db")
    key_file = tmp_path / "data" / ".encryption_key"

    assert key_file.exists()
    assert key_file.read_text(encoding="ascii").strip() == first.encryption_master_key
    assert key_file.stat().st_mode & 0o777 == 0o600

    second = _settings(monkeypatch, tmp_path, DATABASE_URL="sqlite:///./data/app.db")
    assert second.encryption_master_key == first.encryption_master_key


def test_provided_master_key_writes_no_dev_key_file(monkeypatch, tmp_path):
    """Regression: a configured master key must not create a decoy data/.encryption_key."""
    settings = _settings(
        monkeypatch,
        tmp_path,
        JWT_SECRET_KEY=VALID_JWT_SECRET,
        ENCRYPTION_MASTER_KEY=VALID_MASTER_KEY,
        DATABASE_URL="sqlite:///./data/app.db",
    )

    assert settings.encryption_master_key == VALID_MASTER_KEY
    assert not (tmp_path / "data" / ".encryption_key").exists()


def test_validate_master_key_helper():
    validate_master_key(VALID_MASTER_KEY)
    with pytest.raises(ValueError):
        validate_master_key(base64.b64encode(b"too-short").decode())
