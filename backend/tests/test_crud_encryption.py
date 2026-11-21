"""Tests for CRUD operations with envelope encryption support."""

from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import crud
from app.crypto import derive_key, generate_salt
from app.encryption_utils import ContentDecryptionError, EncryptionKeyMissingError
from app.key_cache import key_cache
from app.models import AppConfig, Base, DailyReport, Task


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    yield session
    session.close()
    key_cache.clear()


@pytest.fixture()
def user(db_session):
    return crud.create_user(db_session, "testuser", "hash123")


@pytest.fixture()
def encryption_key():
    return derive_key("test_password", generate_salt())


class TestUpsertDailyReportEncrypted:
    def test_encrypts_when_key_cached(self, db_session, user, encryption_key):
        key_cache.set(user.id, encryption_key)
        report = crud.upsert_daily_report(db_session, user.id, date(2025, 1, 6), "secret note")
        assert report.content_encrypted is not None
        assert report.content_version == 2
        assert report.content_salt is None  # deprecated field no longer written
        # content is decrypted back to plaintext on return
        assert report.content == "secret note"

    def test_refuses_write_when_no_key(self, db_session, user):
        key_cache.remove(user.id)
        with pytest.raises(EncryptionKeyMissingError):
            crud.upsert_daily_report(db_session, user.id, date(2025, 1, 6), "plain note")
        assert crud.get_daily_report(db_session, user.id, date(2025, 1, 6)) is None

    def test_refuses_overwrite_when_no_key(self, db_session, user, encryption_key):
        key_cache.set(user.id, encryption_key)
        crud.upsert_daily_report(db_session, user.id, date(2025, 1, 6), "original")
        key_cache.remove(user.id)
        with pytest.raises(EncryptionKeyMissingError):
            crud.upsert_daily_report(db_session, user.id, date(2025, 1, 6), "overwrite")
        key_cache.set(user.id, encryption_key)
        assert crud.get_daily_report_decrypted(db_session, user.id, date(2025, 1, 6)) == "original"

    def test_decrypt_roundtrip(self, db_session, user, encryption_key):
        key_cache.set(user.id, encryption_key)
        crud.upsert_daily_report(db_session, user.id, date(2025, 1, 7), "roundtrip test")
        decrypted = crud.get_daily_report_decrypted(db_session, user.id, date(2025, 1, 7))
        assert decrypted == "roundtrip test"

    def test_decrypt_legacy_plaintext_record(self, db_session, user):
        # Pre-envelope plaintext rows (written by old versions) stay readable.
        db_session.add(DailyReport(user_id=user.id, date=date(2025, 1, 8), content="old plaintext"))
        db_session.commit()
        decrypted = crud.get_daily_report_decrypted(db_session, user.id, date(2025, 1, 8))
        assert decrypted == "old plaintext"

    def test_decrypt_raises_when_no_key(self, db_session, user, encryption_key):
        key_cache.set(user.id, encryption_key)
        crud.upsert_daily_report(db_session, user.id, date(2025, 1, 9), "encrypted data")
        key_cache.remove(user.id)
        with pytest.raises(ContentDecryptionError):
            crud.get_daily_report_decrypted(db_session, user.id, date(2025, 1, 9))


class TestCreateTaskEncrypted:
    def test_encrypts_when_key_cached(self, db_session, user, encryption_key):
        key_cache.set(user.id, encryption_key)
        task = crud.create_task(db_session, user.id, "secret task")
        assert task.content_encrypted is not None
        assert task.content_version == 2
        assert task.content_salt is None
        # content is decrypted back to plaintext on return
        assert task.content == "secret task"

    def test_refuses_write_when_no_key(self, db_session, user):
        key_cache.remove(user.id)
        with pytest.raises(EncryptionKeyMissingError):
            crud.create_task(db_session, user.id, "plain task")
        assert crud.get_tasks(db_session, user.id) == []

    def test_update_content_refuses_when_no_key(self, db_session, user, encryption_key):
        key_cache.set(user.id, encryption_key)
        task = crud.create_task(db_session, user.id, "original task")
        key_cache.remove(user.id)
        with pytest.raises(EncryptionKeyMissingError):
            crud.update_task(db_session, user.id, task.id, content="overwrite")
        # Non-content updates still work without a key (no plaintext involved)
        updated = crud.update_task(db_session, user.id, task.id, is_completed=True)
        assert updated.is_completed is True

    def test_decrypt_roundtrip(self, db_session, user, encryption_key):
        key_cache.set(user.id, encryption_key)
        task = crud.create_task(db_session, user.id, "roundtrip task")
        decrypted = crud.get_task_decrypted(db_session, user.id, task.id)
        assert decrypted == "roundtrip task"

    def test_decrypt_legacy_plaintext_record(self, db_session, user):
        task = Task(user_id=user.id, content="old plaintext task")
        db_session.add(task)
        db_session.commit()
        decrypted = crud.get_task_decrypted(db_session, user.id, task.id)
        assert decrypted == "old plaintext task"

    def test_decrypt_raises_when_no_key(self, db_session, user, encryption_key):
        key_cache.set(user.id, encryption_key)
        task = crud.create_task(db_session, user.id, "encrypted task")
        key_cache.remove(user.id)
        with pytest.raises(ContentDecryptionError):
            crud.get_task_decrypted(db_session, user.id, task.id)


class TestPlaintextNeverFlushed:
    """Decrypted views must not leak back into the content column via autoflush."""

    def test_read_then_commit_keeps_column_empty(self, db_session, user, encryption_key):
        key_cache.set(user.id, encryption_key)
        crud.upsert_daily_report(db_session, user.id, date(2025, 2, 3), "sensitive text")
        # Reading decrypts into the ORM instance's .content attribute…
        reports = crud.get_daily_reports_by_week(db_session, user.id, date(2025, 2, 3))
        assert reports[0].content == "sensitive text"
        # …and a later query + commit in the same session must NOT flush it back.
        crud.get_tasks(db_session, user.id)
        db_session.commit()
        db_session.expire_all()
        row = crud.get_daily_report(db_session, user.id, date(2025, 2, 3))
        assert row.content == ""
        assert row.content_encrypted is not None


class TestApiKeyNeverFlushed:
    """Decrypted config views must not leak plaintext into the api_key column."""

    def test_read_config_then_commit_keeps_column_encrypted(self, db_session, user, encryption_key):
        key_cache.set(user.id, encryption_key)
        db_session.add(AppConfig(id=1, api_key=crud.encrypt_api_key("sk-secret-key")))
        db_session.commit()

        cfg = crud.get_app_config(db_session)
        assert cfg.api_key == "sk-secret-key"
        # A later commit in the same session (as in report generation) must not
        # flush the decrypted view back into the column.
        crud.save_weekly_report(
            db_session, user.id, date(2025, 1, 6), date(2025, 1, 12), "text", "m"
        )
        db_session.expire_all()
        raw = db_session.get(AppConfig, 1).api_key
        assert raw.startswith("ek1:")
        assert crud.decrypt_api_key(raw) == "sk-secret-key"

    def test_update_config_returns_plaintext_without_dirtying(self, db_session):
        crud.update_app_config(db_session, api_key="sk-another-key")
        db_session.expire_all()
        raw = db_session.get(AppConfig, 1).api_key
        assert raw.startswith("ek1:")
        assert crud.decrypt_api_key(raw) == "sk-another-key"


class TestApiKeyStorage:
    def test_envelope_roundtrip(self):
        stored = crud.encrypt_api_key("sk-test-1234567890")
        assert stored.startswith("ek1:")
        assert crud.decrypt_api_key(stored) == "sk-test-1234567890"

    def test_empty_key(self):
        assert crud.encrypt_api_key("") is None
        assert crud.decrypt_api_key("") is None
        assert crud.decrypt_api_key(None) is None

    def test_legacy_format_still_readable(self):
        import base64

        from app.crypto import encrypt_content

        encrypted = encrypt_content("sk-legacy-key", crud._get_legacy_api_key_encryption_key())
        legacy = base64.b64encode(
            f"{encrypted['ciphertext']}:{encrypted['nonce']}:{encrypted['tag']}".encode()
        ).decode()
        assert crud.decrypt_api_key(legacy) == "sk-legacy-key"

    def test_plaintext_passthrough(self):
        # Very old installs stored keys as plaintext.
        assert crud.decrypt_api_key("sk-plaintext") == "sk-plaintext"
