"""Encryption migration for user data.

This module handles encrypting plaintext content whenever a user logs in.
It checks all content tables for unencrypted records and encrypts them.
"""

import logging

from sqlalchemy.orm import Session

from .crypto import decrypt_content, encrypt_content, generate_salt
from .models import DailyReport, MonthlyReport, Task, User, WeeklyReport

logger = logging.getLogger(__name__)

# Filter condition for unencrypted records: has content but version is not 1
_UNENCRYPTED_FILTER = lambda Model: (
    Model.content.isnot(None),
    Model.content != "",
    Model.content_version.is_(None),
)


def _encrypt_records(records, key: bytes) -> int:
    """Encrypt plaintext records. Returns count of encrypted records."""
    encrypted_count = 0
    for record in records:
        salt = generate_salt()
        encrypted = encrypt_content(record.content, key)
        record.content = ""
        record.content_encrypted = encrypted["ciphertext"]
        record.content_salt = salt.hex()
        record.content_nonce = encrypted["nonce"]
        record.content_tag = encrypted["tag"]
        record.content_version = 1
        encrypted_count += 1
    return encrypted_count


def _cleanup_plaintext_content(db: Session) -> None:
    """Clear plaintext content from records that already have encrypted data.

    This handles the case where content_version=1 but content was not properly
    cleared (a historical bug). These records have both plaintext content and
    encrypted data, which is redundant and potentially a security concern.

    This runs at startup and does NOT require a user key.
    """
    tables = [
        ("daily_reports", DailyReport),
        ("weekly_reports", WeeklyReport),
        ("monthly_reports", MonthlyReport),
        ("tasks", Task),
    ]

    total_cleaned = 0
    for table_name, model in tables:
        # Find records with content_version=1, content non-empty, and encrypted data present
        records = db.query(model).filter(
            model.content_version == 1,
            model.content.isnot(None),
            model.content != "",
            model.content_encrypted.isnot(None),
        ).all()

        for record in records:
            record.content = ""
            total_cleaned += 1

        if records:
            logger.info(
                "Cleaned plaintext from %d %s records (content_version=1 but content not empty)",
                len(records),
                table_name,
            )

    if total_cleaned > 0:
        db.commit()
        logger.info("Total cleaned %d records with stale plaintext content", total_cleaned)


def _fix_old_format_records(db: Session, user_id: int, key: bytes) -> None:
    """Re-encrypt records that were encrypted with the old format (tag='').

    The original encrypt_content() returned tag='' with the GCM tag embedded
    in the ciphertext. The current code separates tag from ciphertext. This
    function re-encrypts old-format records to the new format.

    This requires the user's decryption key (runs on login).
    """
    total_fixed = 0
    tables = [
        ("daily_reports", DailyReport),
        ("weekly_reports", WeeklyReport),
        ("monthly_reports", MonthlyReport),
        ("tasks", Task),
    ]

    for table_name, model in tables:
        # Find records encrypted with old format: content_version=1, has encrypted data, but tag is empty
        records = db.query(model).filter(
            model.user_id == user_id,
            model.content_version == 1,
            model.content_encrypted.isnot(None),
            model.content_tag.is_(None),
        ).all()

        # Also find records where content_tag is empty string (not NULL)
        records += db.query(model).filter(
            model.user_id == user_id,
            model.content_version == 1,
            model.content_encrypted.isnot(None),
            model.content_tag == "",
        ).all()

        # Deduplicate (in case both queries return the same records)
        seen_ids = set()
        unique_records = []
        for r in records:
            if r.id not in seen_ids:
                seen_ids.add(r.id)
                unique_records.append(r)

        for record in unique_records:
            try:
                # Decrypt with old format (tag embedded in ciphertext)
                plaintext = decrypt_content(
                    {
                        "ciphertext": record.content_encrypted,
                        "nonce": record.content_nonce or "",
                        "tag": record.content_tag or "",
                    },
                    key,
                )
                # Re-encrypt with new format (tag separate)
                new_encrypted = encrypt_content(plaintext, key)
                new_salt = generate_salt()
                record.content = ""
                record.content_encrypted = new_encrypted["ciphertext"]
                record.content_salt = new_salt.hex()
                record.content_nonce = new_encrypted["nonce"]
                record.content_tag = new_encrypted["tag"]
                record.content_version = 1
                total_fixed += 1
            except Exception as e:
                logger.warning(
                    "Failed to re-encrypt %s record id=%d: %s",
                    table_name,
                    record.id,
                    e,
                )

        if unique_records:
            logger.info(
                "Re-encrypted %d %s records from old format (tag='') to new format",
                len(unique_records),
                table_name,
            )

    if total_fixed > 0:
        db.commit()
        logger.info("Total re-encrypted %d records to new format", total_fixed)


def migrate_user_encryption(db: Session, user_id: int, key: bytes) -> None:
    """Check and encrypt any plaintext content for a user.

    This is called on every login to ensure API-token-written plaintext
    content gets encrypted when the user logs in via UI.

    Handles three cases:
    1. Records with plaintext content (content_version is NULL) → encrypt them
    2. Records with old encryption format (content_tag='') → re-encrypt to new format
    """
    total_encrypted = 0

    # Case 1: Encrypt plaintext records (content_version is NULL)
    daily_reports = db.query(DailyReport).filter(
        DailyReport.user_id == user_id,
        *_UNENCRYPTED_FILTER(DailyReport),
    ).all()
    total_encrypted += _encrypt_records(daily_reports, key)

    weekly_reports = db.query(WeeklyReport).filter(
        WeeklyReport.user_id == user_id,
        *_UNENCRYPTED_FILTER(WeeklyReport),
    ).all()
    total_encrypted += _encrypt_records(weekly_reports, key)

    monthly_reports = db.query(MonthlyReport).filter(
        MonthlyReport.user_id == user_id,
        *_UNENCRYPTED_FILTER(MonthlyReport),
    ).all()
    total_encrypted += _encrypt_records(monthly_reports, key)

    tasks = db.query(Task).filter(
        Task.user_id == user_id,
        *_UNENCRYPTED_FILTER(Task),
    ).all()
    total_encrypted += _encrypt_records(tasks, key)

    # Case 2: Re-encrypt old format records (content_tag='')
    _fix_old_format_records(db, user_id, key)

    # Mark migration complete
    user = db.query(User).filter(User.id == user_id).first()
    if user and user.needs_encryption_migration:
        user.needs_encryption_migration = False

    if total_encrypted > 0:
        logger.info("Encrypted %d plaintext records for user %d", total_encrypted, user_id)

    db.commit()
