"""Encryption migrations.

- _cleanup_plaintext_content: startup hygiene for a historical bug where
  plaintext was left alongside ciphertext. Runs without any user key.
- migrate_user_to_dek: one-time per-user upgrade from password-derived keys
  to envelope encryption (random DEK wrapped by the server KEK). Runs at
  login, because only then is the legacy password-derived key available.
- migrate_app_config_secret: re-wrap the LLM API key with the KEK so it
  survives restarts (the legacy scheme depended on the JWT secret).
"""

import glob
import logging
import os
import sqlite3
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from .auth import derive_user_key
from .config import settings
from .envelope import CONFIG_SECRET_PREFIX, ensure_user_dek, unwrap_dek, wrap_dek
from .key_cache import key_cache
from .models import AppConfig, DailyReport, MonthlyReport, Task, User, WeeklyReport
from .reencrypt import reencrypt_user_data

logger = logging.getLogger(__name__)


def backup_before_envelope_migration(db: Session) -> str | None:
    """One-time consistent DB snapshot before the irreversible envelope upgrade.

    Taken while any legacy user (wrapped_dek NULL) still exists, using the
    SQLite online backup API so concurrent writers cannot tear the snapshot.
    Skipped for non-SQLite URLs, and once a pre-envelope-*.db file exists in
    the data directory. The snapshot holds legacy ciphertext (decryptable with
    the old login passwords) — it is created 0600 and must be protected like
    the database itself. Returns the backup path, or None when not taken.
    """
    url = settings.database_url
    if not url.startswith("sqlite:///"):
        return None
    db_path = url.replace("sqlite:///", "")
    if not db_path or db_path == ":memory:":
        return None
    has_legacy = db.query(User).filter(User.wrapped_dek.is_(None)).first() is not None
    if not has_legacy:
        return None
    data_dir = os.path.dirname(db_path) or "."
    if glob.glob(os.path.join(data_dir, "pre-envelope-*.db")):
        return None  # snapshot already taken for this data directory

    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    backup_path = os.path.join(data_dir, f"pre-envelope-{stamp}.db")
    fd = os.open(backup_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    os.close(fd)
    try:
        source = sqlite3.connect(db_path)
        try:
            target = sqlite3.connect(backup_path)
            try:
                source.backup(target)
            finally:
                target.close()
        finally:
            source.close()
    except Exception:
        # Never leave a partial snapshot behind: its presence would make every
        # later startup skip the backup (glob marker), silently losing the
        # rollback point. Remove it so the next startup retries.
        try:
            os.remove(backup_path)
        except OSError:
            logger.warning("Could not remove partial backup file %s", backup_path)
        raise
    logger.info("Pre-migration backup saved to %s", backup_path)
    return backup_path


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
        # Find records with encrypted data present but content not cleared
        records = (
            db.query(model)
            .filter(
                model.content_version.isnot(None),
                model.content.isnot(None),
                model.content != "",
                model.content_encrypted.isnot(None),
            )
            .all()
        )

        for record in records:
            record.content = ""
            total_cleaned += 1

        if records:
            logger.info(
                "Cleaned plaintext from %d %s records (encrypted but content not empty)",
                len(records),
                table_name,
            )

    if total_cleaned > 0:
        db.commit()
        logger.info("Total cleaned %d records with stale plaintext content", total_cleaned)


def migrate_user_to_dek(db: Session, user: User, password: str) -> bytes:
    """One-time migration of a legacy user to envelope encryption.

    Derives the legacy password-based key, re-encrypts ALL of the user's
    content under a fresh random DEK, and stores the wrapped DEK — in a
    single transaction. On any failure nothing is committed: wrapped_dek
    stays NULL and the next login retries. Idempotent once wrapped_dek is set.
    """
    if user.wrapped_dek:
        dek = ensure_user_dek(db, user)
        if dek is None:  # pragma: no cover — wrapped_dek set implies a DEK
            dek = unwrap_dek(user.wrapped_dek, user.id)
            key_cache.set(user.id, dek)
        return dek

    old_key = derive_user_key(password, user)
    dek = os.urandom(32)
    try:
        count = reencrypt_user_data(db, user.id, old_key, dek)
        user.wrapped_dek = wrap_dek(dek, user.id)
        user.wrapped_dek_version = 1
        user.needs_encryption_migration = False
        db.commit()
    except Exception:
        db.rollback()
        raise
    # Cache the DEK that actually won in the DB, not the locally generated one:
    # a concurrent login may have committed its own migration first.
    db.refresh(user)
    dek = unwrap_dek(user.wrapped_dek, user.id)
    key_cache.set(user.id, dek)
    logger.info("Migrated user %d to envelope encryption (%d records)", user.id, count)
    return dek


def migrate_app_config_secret(db: Session) -> None:
    """Re-wrap a legacy LLM API key with the KEK (startup, idempotent).

    Legacy values were encrypted with a key derived from JWT_SECRET_KEY, so
    they broke whenever the JWT secret changed (e.g. dev restarts). Values
    that cannot be decrypted are left untouched and logged — re-saving the
    key in Settings repairs them.
    """
    from . import crud

    config = db.query(AppConfig).filter(AppConfig.id == 1).first()
    if not config or not config.api_key or config.api_key.startswith(CONFIG_SECRET_PREFIX):
        return
    plaintext = crud.decrypt_api_key(config.api_key)
    if plaintext is None:
        logger.warning(
            "LLM API key could not be decrypted for envelope re-wrap; "
            "re-save it in Settings to repair."
        )
        return
    config.api_key = crud.encrypt_api_key(plaintext)
    db.commit()
    logger.info("Re-wrapped LLM API key with envelope encryption")
