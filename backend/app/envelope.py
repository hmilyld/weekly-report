"""Envelope encryption: master key → KEK → per-user DEK.

Architecture:
    ENCRYPTION_MASTER_KEY (env / dev key file)
        ──HKDF-SHA256──> KEK (process memory only)
        ──AES-256-GCM wrap──> users.wrapped_dek (stored in DB)
        ──unwrap at startup──> key_cache[user_id] = DEK
        ──AES-256-GCM──> report/task content (content_version=2)

- Each user gets one random 32-byte DEK, generated once and never changed.
  Changing the login password does NOT touch content ciphertext.
- Wrapped DEKs use AAD binding the user identity, so a wrapped key cannot be
  moved between accounts.
- The master key must be backed up together with the database; losing it makes
  all content permanently unreadable.
"""

import base64
import binascii
import logging
import os

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from sqlalchemy.orm import Session

from .config import settings
from .key_cache import key_cache
from .models import User

logger = logging.getLogger(__name__)

KEK_INFO = b"weekly-report/kek/v1"
NONCE_SIZE = 12
TAG_SIZE = 16
DEK_SIZE = 32

# Stored-secret format marker for AppConfig.api_key (envelope-wrapped).
CONFIG_SECRET_PREFIX = "ek1:"
CONFIG_SECRET_AAD = b"app-config:api_key:v1"

_kek: bytes | None = None


def get_kek() -> bytes:
    """Derive (once) the key-encryption key from the configured master key."""
    global _kek
    if _kek is None:
        try:
            master = base64.b64decode(settings.encryption_master_key, validate=True)
        except (binascii.Error, ValueError) as err:
            raise RuntimeError("ENCRYPTION_MASTER_KEY is not valid base64") from err
        if len(master) != DEK_SIZE:
            raise RuntimeError(
                f"ENCRYPTION_MASTER_KEY must decode to exactly {DEK_SIZE} bytes (got {len(master)})"
            )
        _kek = HKDF(
            algorithm=hashes.SHA256(),
            length=DEK_SIZE,
            salt=None,
            info=KEK_INFO,
        ).derive(master)
    return _kek


def _dek_aad(user_id: int) -> bytes:
    return f"user:{user_id}:dek:v1".encode()


def _seal(plaintext: bytes, aad: bytes) -> str:
    """AES-GCM seal with the KEK; returns base64(nonce | ciphertext | tag)."""
    nonce = os.urandom(NONCE_SIZE)
    ct_with_tag = AESGCM(get_kek()).encrypt(nonce, plaintext, aad)
    return base64.b64encode(nonce + ct_with_tag).decode()


def _open(wrapped: str, aad: bytes) -> bytes:
    raw = base64.b64decode(wrapped, validate=True)
    if len(raw) < NONCE_SIZE + TAG_SIZE:
        raise ValueError("Wrapped key is too short")
    return AESGCM(get_kek()).decrypt(raw[:NONCE_SIZE], raw[NONCE_SIZE:], aad)


def wrap_dek(dek: bytes, user_id: int) -> str:
    if len(dek) != DEK_SIZE:
        raise ValueError(f"DEK must be {DEK_SIZE} bytes")
    return _seal(dek, _dek_aad(user_id))


def unwrap_dek(wrapped: str, user_id: int) -> bytes:
    dek = _open(wrapped, _dek_aad(user_id))
    if len(dek) != DEK_SIZE:
        raise ValueError("Unwrapped DEK has wrong length")
    return dek


def provision_user_dek(db: Session, user: User) -> bytes:
    """Create a fresh DEK for a brand-new user (no legacy data to migrate)."""
    dek = os.urandom(DEK_SIZE)
    user.wrapped_dek = wrap_dek(dek, user.id)
    user.wrapped_dek_version = 1
    user.needs_encryption_migration = False
    db.commit()
    key_cache.set(user.id, dek)
    return dek


def ensure_user_dek(db: Session, user: User) -> bytes | None:
    """Return the user's DEK, unwrapping from the DB if the cache is empty.

    Returns None when the user has not been migrated yet (wrapped_dek is NULL).
    Raises on unwrap failure (wrong master key / corrupted wrapped key).
    """
    key = key_cache.get(user.id)
    if key:
        return key
    if not user.wrapped_dek:
        return None
    dek = unwrap_dek(user.wrapped_dek, user.id)
    key_cache.set(user.id, dek)
    return dek


def load_all_user_deks(db: Session) -> list[int]:
    """Populate key_cache from the DB at startup. Returns ids that failed.

    A failure for one user must not block the whole app: that user's reads
    will report decryption failure until the master key issue is fixed.
    """
    failed: list[int] = []
    users = db.query(User).filter(User.wrapped_dek.isnot(None)).all()
    for user in users:
        try:
            key_cache.set(user.id, unwrap_dek(user.wrapped_dek, user.id))
        except Exception as err:
            failed.append(user.id)
            logger.error(
                "Failed to unwrap DEK for user id=%d username=%s: %s",
                user.id,
                user.username,
                err,
            )
    return failed


def wrap_config_secret(plaintext: str) -> str:
    """Envelope-wrap an app-level secret (LLM API key)."""
    return CONFIG_SECRET_PREFIX + _seal(plaintext.encode("utf-8"), CONFIG_SECRET_AAD)


def unwrap_config_secret(stored: str) -> str:
    if not stored.startswith(CONFIG_SECRET_PREFIX):
        raise ValueError("Not an envelope-wrapped config secret")
    return _open(stored[len(CONFIG_SECRET_PREFIX) :], CONFIG_SECRET_AAD).decode("utf-8")
