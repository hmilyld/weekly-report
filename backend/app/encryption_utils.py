"""Shared encryption/decryption utilities for reports."""

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from .crypto import decrypt_content, encrypt_content, generate_salt
from .key_cache import key_cache


def decrypt_daily_entries(dailies: list, user_id: int) -> list[tuple[str, str]]:
    """Decrypt daily report entries and return (date_str, content) tuples."""
    key = key_cache.get(user_id)
    entries = []
    for d in dailies:
        if d.content_encrypted and key:
            encrypted_data = {
                "ciphertext": d.content_encrypted,
                "nonce": d.content_nonce or "",
                "tag": d.content_tag or "",
            }
            content = decrypt_content(encrypted_data, key)
        else:
            content = d.content
        if content.strip():
            entries.append((str(d.date), content))
    return entries


def encrypt_model_content(report, content: str, user_id: int) -> None:
    """Encrypt content and set encryption fields on the report model."""
    key = key_cache.get(user_id)
    if key:
        salt = generate_salt()
        encrypted = encrypt_content(content, key)
        report.content = ""
        report.content_encrypted = encrypted["ciphertext"]
        report.content_salt = salt.hex()
        report.content_nonce = encrypted["nonce"]
        report.content_tag = encrypted["tag"]
        report.content_version = 1
    else:
        report.content = content
        report.content_encrypted = None
        report.content_salt = None
        report.content_nonce = None
        report.content_tag = None
        report.content_version = None


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
    from .crud import _decrypt_model_content

    _decrypt_model_content(report, user_id)
