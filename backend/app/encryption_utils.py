"""Centralized content encryption/decryption for all report/task models.

content_version semantics:
    1 (or NULL) — legacy: key derived from the login password, no AAD
    2           — envelope: per-user DEK from key_cache, AAD binds table + user

Writes without a DEK are REFUSED (EncryptionKeyMissingError → HTTP 409);
content is never silently stored as plaintext.
"""

from datetime import UTC, datetime

from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import set_committed_value

from .crypto import decrypt_content, encrypt_content
from .key_cache import key_cache

CONTENT_VERSION_LEGACY = 1
CONTENT_VERSION_DEK = 2


class EncryptionKeyMissingError(RuntimeError):
    """No DEK available for this user; the write must be refused."""


class ContentDecryptionError(RuntimeError):
    """Encrypted content could not be decrypted; callers must fail loudly."""


def content_aad(model, user_id: int) -> bytes:
    """Bind ciphertext to its table and owner (prevents cross-record swaps)."""
    return f"{model.__tablename__}:{user_id}".encode()


def set_encrypted_content(
    model, content: str, user_id: int, key: bytes, version: int = CONTENT_VERSION_DEK
) -> None:
    """Encrypt content with an explicit key and set all encryption fields."""
    aad = content_aad(model, user_id) if version == CONTENT_VERSION_DEK else None
    encrypted = encrypt_content(content, key, aad=aad)
    model.content = ""
    model.content_encrypted = encrypted["ciphertext"]
    model.content_salt = None  # deprecated dead field — no longer written
    model.content_nonce = encrypted["nonce"]
    model.content_tag = encrypted["tag"]
    model.content_version = version


def encrypt_model_content(report, content: str, user_id: int) -> None:
    """Encrypt content with the user's cached DEK; refuse if no key exists."""
    key = key_cache.get(user_id)
    if not key:
        raise EncryptionKeyMissingError(f"No encryption key available for user {user_id}")
    set_encrypted_content(report, content, user_id, key)


def decrypt_record_content(model, user_id: int) -> str:
    """Decrypt one record's content; raise ContentDecryptionError on failure."""
    key = key_cache.get(user_id)
    if not key:
        raise ContentDecryptionError(f"No encryption key available for user {user_id}")
    aad = content_aad(model, user_id) if model.content_version == CONTENT_VERSION_DEK else None
    try:
        return decrypt_content(
            {
                "ciphertext": model.content_encrypted,
                "nonce": model.content_nonce or "",
                "tag": model.content_tag or "",
            },
            key,
            aad=aad,
        )
    except Exception as err:
        raise ContentDecryptionError(
            f"Failed to decrypt {model.__tablename__} record {model.id}"
        ) from err


def decrypt_model_content(model, user_id: int) -> None:
    """Decrypt content_encrypted back into content on a model instance.

    On failure (key missing after restart, wrong master key, corrupted data),
    sets _decryption_failed so the frontend can surface it.
    """
    if not model.content_encrypted:
        return
    try:
        plaintext = decrypt_record_content(model, user_id)
        # Set WITHOUT marking the attribute dirty: decrypted plaintext must
        # never be autoflushed back into the content column (the root cause
        # of the historical "plaintext left beside ciphertext" bug).
        set_committed_value(model, "content", plaintext)
        model._decryption_failed = False
    except ContentDecryptionError:
        model._decryption_failed = True


# Backwards-compatible name used across crud/routers.
_decrypt_model_content = decrypt_model_content


def decrypt_daily_entries(dailies: list, user_id: int) -> list[tuple[str, str]]:
    """Decrypt daily entries for LLM generation, returning (date_str, content).

    Raises ContentDecryptionError if ANY encrypted entry cannot be read —
    generating a report from silently missing entries is worse than failing.
    """
    entries = []
    for d in dailies:
        content = decrypt_record_content(d, user_id) if d.content_encrypted else d.content
        if content.strip():
            entries.append((str(d.date), content))
    return entries


def update_report_content(
    db: Session,
    report,
    content: str,
    user_id: int,
) -> None:
    """Update report content with encryption, commit and refresh."""
    encrypt_model_content(report, content, user_id)
    report.generated_at = datetime.now(UTC)
    db.commit()
    db.refresh(report)
    decrypt_model_content(report, user_id)
