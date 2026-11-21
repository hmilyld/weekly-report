"""Data layer: SQLite pragmas and safe plaintext cleanup."""

from datetime import date

from sqlalchemy import create_engine

from app import crud
from app.auth import hash_password
from app.envelope import provision_user_dek
from app.key_cache import key_cache
from app.migration import cleanup_plaintext_content
from app.models import DailyReport


def _user_with_entry(db, username="alice"):
    user = crud.create_user(db, username, hash_password("Passw0rd1"))
    provision_user_dek(db, user)
    report = crud.upsert_daily_report(db, user.id, date(2026, 11, 17), "真实内容")
    return user, report


def _leave_plaintext(db, report_id):
    """Reproduce the historical bug: plaintext next to ciphertext."""
    row = db.query(DailyReport).filter(DailyReport.id == report_id).first()
    row.content = "明文残留"
    db.commit()
    return row


class TestSqlitePragmas:
    def test_new_engines_get_wal_and_foreign_keys(self, tmp_path):
        engine = create_engine(f"sqlite:///{tmp_path / 'probe.db'}")

        with engine.connect() as conn:
            assert conn.exec_driver_sql("PRAGMA journal_mode").scalar().lower() == "wal"
            assert conn.exec_driver_sql("PRAGMA foreign_keys").scalar() == 1
            assert conn.exec_driver_sql("PRAGMA busy_timeout").scalar() == 5000

        engine.dispose()


class TestPlaintextCleanup:
    def test_clears_plaintext_when_ciphertext_is_readable(self, api_env):
        _client, db = api_env
        _user, report = _user_with_entry(db)
        _leave_plaintext(db, report.id)

        cleaned = cleanup_plaintext_content(db)

        db.expire_all()
        row = db.query(DailyReport).filter(DailyReport.id == report.id).first()
        assert cleaned == 1
        assert row.content == ""
        assert row.content_encrypted

    def test_clears_plaintext_with_a_cold_key_cache(self, api_env):
        """Startup runs before load_all_user_deks; the DEK must be unwrapped on demand."""
        _client, db = api_env
        _user, report = _user_with_entry(db)
        _leave_plaintext(db, report.id)
        key_cache.clear()

        cleaned = cleanup_plaintext_content(db)

        db.expire_all()
        row = db.query(DailyReport).filter(DailyReport.id == report.id).first()
        assert cleaned == 1
        assert row.content == ""

    def test_keeps_plaintext_for_unmigrated_legacy_user(self, api_env):
        _client, db = api_env
        user, report = _user_with_entry(db)
        _leave_plaintext(db, report.id)
        user.wrapped_dek = None  # legacy user: no DEK until the login migration
        db.commit()
        key_cache.remove(user.id)

        cleaned = cleanup_plaintext_content(db)

        db.expire_all()
        row = db.query(DailyReport).filter(DailyReport.id == report.id).first()
        assert cleaned == 0
        assert row.content == "明文残留"

    def test_keeps_plaintext_when_wrapped_dek_is_corrupted(self, api_env):
        _client, db = api_env
        user, report = _user_with_entry(db)
        _leave_plaintext(db, report.id)
        user.wrapped_dek = "not-a-valid-wrapped-dek"
        db.commit()
        key_cache.remove(user.id)

        cleaned = cleanup_plaintext_content(db)

        db.expire_all()
        row = db.query(DailyReport).filter(DailyReport.id == report.id).first()
        assert cleaned == 0
        assert row.content == "明文残留"

    def test_keeps_plaintext_when_ciphertext_is_corrupted(self, api_env):
        _client, db = api_env
        _user, report = _user_with_entry(db)
        row = _leave_plaintext(db, report.id)
        row.content_encrypted = "not-valid-ciphertext"
        db.commit()

        cleaned = cleanup_plaintext_content(db)

        db.expire_all()
        row = db.query(DailyReport).filter(DailyReport.id == report.id).first()
        assert cleaned == 0
        assert row.content == "明文残留"
