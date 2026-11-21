"""Startup schema migration and bootstrap for the SQLite database.

Additive only: SQLite cannot drop or retype a column in place, so new columns are
added one at a time and every failure is logged with its table/column.
"""

import logging

from sqlalchemy import inspect, text

from .database import Base, SessionLocal, engine
from .migration import backup_before_envelope_migration, cleanup_plaintext_content
from .models import AppConfig

logger = logging.getLogger(__name__)

USER_COLUMN_MIGRATIONS = (
    ("password_version", "INTEGER NOT NULL DEFAULT 0"),
    ("role", "VARCHAR(20) NOT NULL DEFAULT 'user'"),
    ("needs_encryption_migration", "BOOLEAN NOT NULL DEFAULT 1"),
    ("last_login_at", "DATETIME"),
    ("wrapped_dek", "TEXT"),
    ("wrapped_dek_version", "INTEGER NOT NULL DEFAULT 1"),
)

CONTENT_COLUMN_MIGRATIONS = (
    ("content_encrypted", "TEXT"),
    ("content_salt", "VARCHAR(64)"),
    ("content_nonce", "VARCHAR(64)"),
    ("content_tag", "VARCHAR(64)"),
    ("content_version", "INTEGER"),
)

CONTENT_TABLES = ("daily_reports", "weekly_reports", "tasks", "monthly_reports")


def _existing_tables() -> set[str]:
    try:
        return set(inspect(engine).get_table_names())
    except Exception:
        logger.exception("Cannot inspect existing tables; skipping schema migration")
        return set()


def _add_missing_columns(table: str, migrations: tuple[tuple[str, str], ...]) -> set[str]:
    """Add any missing columns; return the column set as it was before migrating."""
    columns = {column["name"] for column in inspect(engine).get_columns(table)}
    for column_name, definition in migrations:
        if column_name in columns:
            continue
        try:
            with engine.begin() as connection:
                connection.execute(
                    text(f"ALTER TABLE {table} ADD COLUMN {column_name} {definition}")
                )
        except Exception:
            logger.exception("Migration failed for %s.%s", table, column_name)
        else:
            logger.info("Migration added %s.%s", table, column_name)
    return columns


def migrate_schema() -> None:
    """Bring an existing database up to the current schema."""
    tables = _existing_tables()

    if "users" in tables:
        before = _add_missing_columns("users", USER_COLUMN_MIGRATIONS)
        if "role" not in before:
            # Column just added: the very first account is the administrator.
            with engine.begin() as connection:
                connection.execute(text("UPDATE users SET role = 'admin' WHERE id = 1"))
    else:
        logger.info("users table does not exist yet (first run)")

    for table in CONTENT_TABLES:
        if table in tables:
            _add_missing_columns(table, CONTENT_COLUMN_MIGRATIONS)


def _seed_app_config() -> None:
    with SessionLocal() as db:
        if db.query(AppConfig).filter(AppConfig.id == 1).first():
            return
        db.add(
            AppConfig(
                id=1,
                llm_api_url="http://localhost:11434/v1/chat/completions",
                llm_model_name="llama2",
                api_key="",
            )
        )
        db.commit()


def init_database() -> None:
    """Create tables, migrate, snapshot before the envelope upgrade, seed."""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created/verified")
        migrate_schema()
        # One-time safety snapshot BEFORE any destructive upgrade step, so the
        # irreversible envelope migration always has a rollback point.
        with SessionLocal() as backup_db:
            backup_path = backup_before_envelope_migration(backup_db)
        if backup_path:
            logger.warning(
                "Pre-migration backup saved: %s (0600, keep until upgrade verified)", backup_path
            )
        with SessionLocal() as cleanup_db:
            cleanup_plaintext_content(cleanup_db)
    except Exception:
        logger.exception("Database init failed")
        raise
    _seed_app_config()
