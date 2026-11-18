"""One-shot re-encryption of a user's legacy data onto their new DEK.

Used only by migration.migrate_user_to_dek during the envelope-encryption
upgrade. Handles plaintext records and both legacy ciphertext formats
(tag separated or embedded). Does NOT commit: the caller wraps the data
rewrite and the wrapped_dek write in a single transaction.
"""

from sqlalchemy.orm import Session

from .crypto import decrypt_content
from .encryption_utils import set_encrypted_content
from .models import DailyReport, MonthlyReport, Task, WeeklyReport


def reencrypt_user_data(db: Session, user_id: int, old_key: bytes, new_key: bytes) -> int:
    """Re-encrypt all of a user's content from old_key to new_key.

    Returns the number of records rewritten. Raises on any decryption failure
    so the caller can roll back — partial migration is never committed.
    """
    count = 0
    for model in (DailyReport, WeeklyReport, MonthlyReport, Task):
        for record in db.query(model).filter(model.user_id == user_id).all():
            if record.content_encrypted:
                # Legacy ciphertext: no AAD; decrypt_content tolerates the
                # old format where the GCM tag is embedded in the ciphertext.
                plaintext = decrypt_content(
                    {
                        "ciphertext": record.content_encrypted,
                        "nonce": record.content_nonce or "",
                        "tag": record.content_tag or "",
                    },
                    old_key,
                )
            elif record.content:
                plaintext = record.content
            else:
                continue
            set_encrypted_content(record, plaintext, user_id, new_key)
            count += 1
    db.flush()
    return count
