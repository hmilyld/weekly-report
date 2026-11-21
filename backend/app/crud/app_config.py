"""App config persistence and LLM API key wrapping.

New writes use the envelope scheme (KEK-wrapped). The legacy branch exists only
so installs that still hold a JWT-secret-derived ciphertext keep working until
``migration.migrate_app_config_secret`` re-wraps it.
"""

import base64
import hashlib
import logging
from datetime import UTC, datetime

from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import set_committed_value

from .. import models
from ..config import settings
from ..crypto import decrypt_content
from ..envelope import CONFIG_SECRET_PREFIX, unwrap_config_secret, wrap_config_secret

logger = logging.getLogger(__name__)


def _get_legacy_api_key_encryption_key() -> bytes:
    """LEGACY: derive the old API-key encryption key from the JWT secret.

    Kept only to read pre-envelope values; new writes use envelope wrapping.
    """
    return hashlib.pbkdf2_hmac(
        "sha256",
        settings.jwt_secret_key.encode(),
        b"api_key_encryption_salt",
        100000,
        dklen=32,
    )


def _looks_like_legacy_encrypted(value: str) -> bool:
    """True if value matches the legacy base64('ct:nonce:tag') format."""
    try:
        decoded = base64.b64decode(value, validate=True).decode("utf-8")
    except Exception:
        return False
    return decoded.count(":") == 2


def encrypt_api_key(api_key: str) -> str | None:
    """Envelope-encrypt the LLM API key for storage (survives restarts)."""
    if not api_key:
        return None
    return wrap_config_secret(api_key)


def decrypt_api_key(encrypted_api_key: str) -> str | None:
    """Decrypt a stored LLM API key (envelope format, with legacy fallback)."""
    if not encrypted_api_key:
        return None
    if encrypted_api_key.startswith(CONFIG_SECRET_PREFIX):
        try:
            return unwrap_config_secret(encrypted_api_key)
        except Exception:
            logger.error(
                "Failed to unwrap LLM API key — check ENCRYPTION_MASTER_KEY; "
                "re-save the key in Settings to repair."
            )
            return None
    if not _looks_like_legacy_encrypted(encrypted_api_key):
        # Very old installs stored the key as plaintext; pass through so it
        # keeps working and gets re-wrapped by migrate_app_config_secret().
        return encrypted_api_key
    try:
        decoded = base64.b64decode(encrypted_api_key).decode()
        ciphertext, nonce, tag = decoded.split(":")
        return decrypt_content(
            {"ciphertext": ciphertext, "nonce": nonce, "tag": tag},
            _get_legacy_api_key_encryption_key(),
        )
    except Exception:
        logger.warning(
            "Legacy LLM API key could not be decrypted (JWT secret changed?); "
            "re-save the key in Settings."
        )
        return None


def get_app_config(db: Session) -> models.AppConfig:
    """Return the singleton config, creating it on first use.

    The LLM API key is decrypted into the returned object via
    ``set_committed_value`` so a later commit never writes plaintext back.
    """
    config = db.query(models.AppConfig).filter(models.AppConfig.id == 1).first()
    if not config:
        config = models.AppConfig(id=1)
        db.add(config)
        db.commit()
        db.refresh(config)
    if config.api_key:
        set_committed_value(config, "api_key", decrypt_api_key(config.api_key))
    return config


def update_app_config(
    db: Session,
    llm_api_url: str | None = None,
    llm_model_name: str | None = None,
    api_key: str | None = None,
) -> models.AppConfig:
    config = db.query(models.AppConfig).filter(models.AppConfig.id == 1).first()
    if not config:
        config = models.AppConfig(id=1)
        db.add(config)
    if llm_api_url is not None:
        config.llm_api_url = llm_api_url
    if llm_model_name is not None:
        config.llm_model_name = llm_model_name
    # Callers pass None for "unchanged"; masked values are filtered in the router,
    # so a real key containing '*' can be stored.
    if api_key is not None:
        config.api_key = encrypt_api_key(api_key)
    config.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(config)
    # Return with decrypted API key (clean attribute — never flushed back).
    set_committed_value(
        config, "api_key", decrypt_api_key(config.api_key) if config.api_key else None
    )
    return config
