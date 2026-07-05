"""Re-encrypt all user data when password changes."""

from sqlalchemy.orm import Session

from .crypto import decrypt_content, encrypt_content, generate_salt
from .models import DailyReport, Task, WeeklyReport


def reencrypt_user_data(db: Session, user_id: int, old_key: bytes, new_key: bytes) -> None:
    # Re-encrypt daily reports
    for report in db.query(DailyReport).filter(DailyReport.user_id == user_id).all():
        if report.content_encrypted:
            plaintext = decrypt_content(
                {
                    "ciphertext": report.content_encrypted,
                    "nonce": report.content_nonce or "",
                    "tag": report.content_tag or "",
                },
                old_key,
            )
            new_encrypted = encrypt_content(plaintext, new_key)
            salt = generate_salt()
            report.content = ""
            report.content_encrypted = new_encrypted["ciphertext"]
            report.content_salt = salt.hex()
            report.content_nonce = new_encrypted["nonce"]
            report.content_tag = new_encrypted["tag"]

    # Re-encrypt weekly reports
    for report in db.query(WeeklyReport).filter(WeeklyReport.user_id == user_id).all():
        if report.content_encrypted:
            plaintext = decrypt_content(
                {
                    "ciphertext": report.content_encrypted,
                    "nonce": report.content_nonce or "",
                    "tag": report.content_tag or "",
                },
                old_key,
            )
            new_encrypted = encrypt_content(plaintext, new_key)
            salt = generate_salt()
            report.content = ""
            report.content_encrypted = new_encrypted["ciphertext"]
            report.content_salt = salt.hex()
            report.content_nonce = new_encrypted["nonce"]
            report.content_tag = new_encrypted["tag"]

    # Re-encrypt tasks
    for task in db.query(Task).filter(Task.user_id == user_id).all():
        if task.content_encrypted:
            plaintext = decrypt_content(
                {
                    "ciphertext": task.content_encrypted,
                    "nonce": task.content_nonce or "",
                    "tag": task.content_tag or "",
                },
                old_key,
            )
            new_encrypted = encrypt_content(plaintext, new_key)
            salt = generate_salt()
            task.content = ""
            task.content_encrypted = new_encrypted["ciphertext"]
            task.content_salt = salt.hex()
            task.content_nonce = new_encrypted["nonce"]
            task.content_tag = new_encrypted["tag"]

    db.commit()
