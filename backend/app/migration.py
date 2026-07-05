"""One-time encryption migration for user data."""

from sqlalchemy.orm import Session

from .crypto import encrypt_content, generate_salt
from .models import DailyReport, Task, User, WeeklyReport


def migrate_user_encryption(db: Session, user_id: int, key: bytes) -> None:
    """Migrate existing plaintext daily reports, weekly reports, and tasks to encrypted form."""
    # Migrate daily reports
    daily_reports = db.query(DailyReport).filter(DailyReport.user_id == user_id).all()
    for report in daily_reports:
        if report.content and not report.content_encrypted:
            salt = generate_salt()
            encrypted = encrypt_content(report.content, key)
            report.content = ""
            report.content_encrypted = encrypted["ciphertext"]
            report.content_salt = salt.hex()
            report.content_nonce = encrypted["nonce"]
            report.content_tag = encrypted["tag"]
            report.content_version = 1

    # Migrate weekly reports
    weekly_reports = db.query(WeeklyReport).filter(WeeklyReport.user_id == user_id).all()
    for report in weekly_reports:
        if report.content and not report.content_encrypted:
            salt = generate_salt()
            encrypted = encrypt_content(report.content, key)
            report.content = ""
            report.content_encrypted = encrypted["ciphertext"]
            report.content_salt = salt.hex()
            report.content_nonce = encrypted["nonce"]
            report.content_tag = encrypted["tag"]
            report.content_version = 1

    # Migrate tasks
    tasks = db.query(Task).filter(Task.user_id == user_id).all()
    for task in tasks:
        if task.content and not task.content_encrypted:
            salt = generate_salt()
            encrypted = encrypt_content(task.content, key)
            task.content = ""
            task.content_encrypted = encrypted["ciphertext"]
            task.content_salt = salt.hex()
            task.content_nonce = encrypted["nonce"]
            task.content_tag = encrypted["tag"]
            task.content_version = 1

    # Mark migration complete
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        user.needs_encryption_migration = False

    db.commit()
