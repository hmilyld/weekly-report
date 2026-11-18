"""Tests for the one-time pre-migration database snapshot."""

import os
import sqlite3
import stat

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import crud
from app.config import settings
from app.envelope import provision_user_dek
from app.key_cache import key_cache
from app.migration import backup_before_envelope_migration
from app.models import Base


@pytest.fixture()
def file_db(tmp_path, monkeypatch):
    db_path = tmp_path / "weekly_report.db"
    url = f"sqlite:///{db_path}"
    monkeypatch.setattr(settings, "database_url", url)
    engine = create_engine(url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session, db_path
    session.close()
    key_cache.clear()


class TestPreMigrationBackup:
    def test_snapshot_created_for_legacy_user(self, file_db):
        db, _ = file_db
        crud.create_user(db, "legacy", "hash")
        path = backup_before_envelope_migration(db)
        assert path is not None
        assert os.path.exists(path)
        assert stat.S_IMODE(os.stat(path).st_mode) == 0o600
        # Snapshot is a readable, consistent copy of the database.
        conn = sqlite3.connect(path)
        try:
            assert conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 1
        finally:
            conn.close()

    def test_one_time_only(self, file_db):
        db, _ = file_db
        crud.create_user(db, "legacy", "hash")
        first = backup_before_envelope_migration(db)
        assert first is not None
        # A second startup must not create another snapshot.
        assert backup_before_envelope_migration(db) is None

    def test_skipped_when_all_users_migrated(self, file_db):
        db, _ = file_db
        user = crud.create_user(db, "modern", "hash")
        provision_user_dek(db, user)
        assert backup_before_envelope_migration(db) is None

    def test_skipped_for_non_sqlite_url(self, file_db, monkeypatch):
        db, _ = file_db
        crud.create_user(db, "legacy", "hash")
        monkeypatch.setattr(settings, "database_url", "postgresql://localhost/weekly")
        assert backup_before_envelope_migration(db) is None

    def test_skipped_for_empty_database(self, file_db):
        db, _ = file_db
        assert backup_before_envelope_migration(db) is None
