"""Database setup with SQLAlchemy."""

import os
import sqlite3

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import declarative_base, sessionmaker

from .config import settings, sqlite_data_dir

# Ensure the data directory exists (SQLite only; other URLs are left untouched).
db_dir = sqlite_data_dir(settings.database_url)
if db_dir != ".":
    os.makedirs(db_dir, exist_ok=True)

_is_sqlite = settings.database_url.startswith("sqlite:")

engine = create_engine(
    settings.database_url,
    # SQLite connections are handed to FastAPI's threadpool workers.
    connect_args={"check_same_thread": False} if _is_sqlite else {},
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


@event.listens_for(Engine, "connect")
def _sqlite_pragmas(dbapi_connection, connection_record):
    """WAL + foreign keys + a busy timeout for multi-user concurrency.

    The default rollback journal lets one writer block every reader; WAL keeps
    reads non-blocking. Without ``foreign_keys`` SQLite silently ignores the
    FOREIGN KEY declarations in models.py. Registered on Engine (not just this
    engine) so test engines behave the same way.
    """
    if not isinstance(dbapi_connection, sqlite3.Connection):
        return
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA busy_timeout=5000")
    finally:
        cursor.close()


def get_db():
    """Dependency: one session per request, committed on success.

    Committing here (instead of only inside CRUD helpers) keeps bookkeeping
    writes such as API-token usage durable, and guarantees a rollback whenever
    the endpoint raises.
    """
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    else:
        db.commit()
    finally:
        db.close()
