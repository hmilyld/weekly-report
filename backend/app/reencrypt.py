"""Re-encrypt all user data when password changes."""

from sqlalchemy.orm import Session

from .crypto import decrypt_content, encrypt_content, generate_salt
from .models import DailyReport, MonthlyReport, Task, WeeklyReport


def reencrypt_user_data(db: Session, user_id: int, old_key: bytes, new_key: bytes) -> None:
    """Re-encrypt all user content with new key.

    Handles both already-encrypted records (decrypt with old_key, encrypt with new_key)
    and plaintext records (just encrypt with new_key).
    """

    def _reencrypt_record(record, old_key: bytes, new_key: bytes) -> None:
        """Re-encrypt a single record."""
        if record.content_encrypted:
            # Already encrypted: decrypt with old key, encrypt with new key
            plaintext = decrypt_content(
                {
                    "ciphertext": record.content_encrypted,
                    "nonce": record.content_nonce or "",
                    "tag": record.content_tag or "",
                },
                old_key,
            )
            new_encrypted = encrypt_content(plaintext, new_key)
            salt = generate_salt()
            record.content = ""
            record.content_encrypted = new_encrypted["ciphertext"]
            record.content_salt = salt.hex()
            record.content_nonce = new_encrypted["nonce"]
            record.content_tag = new_encrypted["tag"]
            record.content_version = 1
        elif record.content:
            # Plaintext: just encrypt with new key
            new_encrypted = encrypt_content(record.content, new_key)
            salt = generate_salt()
            record.content = ""
            record.content_encrypted = new_encrypted["ciphertext"]
            record.content_salt = salt.hex()
            record.content_nonce = new_encrypted["nonce"]
            record.content_tag = new_encrypted["tag"]
            record.content_version = 1

    # Re-encrypt daily reports
    for report in db.query(DailyReport).filter(DailyReport.user_id == user_id).all():
        _reencrypt_record(report, old_key, new_key)

    # Re-encrypt weekly reports
    for report in db.query(WeeklyReport).filter(WeeklyReport.user_id == user_id).all():
        _reencrypt_record(report, old_key, new_key)

    # Re-encrypt monthly reports
    for report in db.query(MonthlyReport).filter(MonthlyReport.user_id == user_id).all():
        _reencrypt_record(report, old_key, new_key)

    # Re-encrypt tasks
    for task in db.query(Task).filter(Task.user_id == user_id).all():
        _reencrypt_record(task, old_key, new_key)

    db.commit()
