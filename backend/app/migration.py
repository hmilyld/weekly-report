"""Encryption migration for user data.

This module handles encrypting plaintext content whenever a user logs in.
It checks all content tables for unencrypted records and encrypts them.
"""

import logging

from sqlalchemy.orm import Session

from .crypto import encrypt_content, generate_salt
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


def migrate_user_encryption(db: Session, user_id: int, key: bytes) -> None:
    """Check and encrypt any plaintext content for a user.

    This is called on every login to ensure API-token-written plaintext
    content gets encrypted when the user logs in via UI.

    Only queries records that need encryption (content_version is NULL).
    """
    total_encrypted = 0

    # Query only unencrypted daily reports
    daily_reports = db.query(DailyReport).filter(
        DailyReport.user_id == user_id,
        *_UNENCRYPTED_FILTER(DailyReport),
    ).all()
    total_encrypted += _encrypt_records(daily_reports, key)

    # Query only unencrypted weekly reports
    weekly_reports = db.query(WeeklyReport).filter(
        WeeklyReport.user_id == user_id,
        *_UNENCRYPTED_FILTER(WeeklyReport),
    ).all()
    total_encrypted += _encrypt_records(weekly_reports, key)

    # Query only unencrypted monthly reports
    monthly_reports = db.query(MonthlyReport).filter(
        MonthlyReport.user_id == user_id,
        *_UNENCRYPTED_FILTER(MonthlyReport),
    ).all()
    total_encrypted += _encrypt_records(monthly_reports, key)

    # Query only unencrypted tasks
    tasks = db.query(Task).filter(
        Task.user_id == user_id,
        *_UNENCRYPTED_FILTER(Task),
    ).all()
    total_encrypted += _encrypt_records(tasks, key)

    # Mark migration complete
    user = db.query(User).filter(User.id == user_id).first()
    if user and user.needs_encryption_migration:
        user.needs_encryption_migration = False

    if total_encrypted > 0:
        logger.info("Encrypted %d plaintext records for user %d", total_encrypted, user_id)

    db.commit()
