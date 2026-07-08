"""Tests for CRUD operations with encryption support."""

from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import crud
from app.crypto import derive_key, generate_salt
from app.key_cache import key_cache
from app.models import Base


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
        assert report.content_salt is not None
        assert report.content_version == 1
        # content is decrypted back to plaintext on return
        assert report.content == "secret note"

    def test_plaintext_when_no_key(self, db_session, user):
        key_cache.remove(user.id)
        report = crud.upsert_daily_report(db_session, user.id, date(2025, 1, 6), "plain note")
        assert report.content == "plain note"
        assert report.content_encrypted is None

    def test_decrypt_roundtrip(self, db_session, user, encryption_key):
        key_cache.set(user.id, encryption_key)
        crud.upsert_daily_report(db_session, user.id, date(2025, 1, 7), "roundtrip test")
        decrypted = crud.get_daily_report_decrypted(db_session, user.id, date(2025, 1, 7))
        assert decrypted == "roundtrip test"

    def test_decrypt_fallback_to_plaintext(self, db_session, user):
        key_cache.remove(user.id)
        crud.upsert_daily_report(db_session, user.id, date(2025, 1, 8), "old plaintext")
        decrypted = crud.get_daily_report_decrypted(db_session, user.id, date(2025, 1, 8))
        assert decrypted == "old plaintext"

    def test_decrypt_returns_none_when_no_key(self, db_session, user, encryption_key):
        key_cache.set(user.id, encryption_key)
        crud.upsert_daily_report(db_session, user.id, date(2025, 1, 9), "encrypted data")
        key_cache.remove(user.id)
        decrypted = crud.get_daily_report_decrypted(db_session, user.id, date(2025, 1, 9))
        assert decrypted is None


class TestCreateTaskEncrypted:
    def test_encrypts_when_key_cached(self, db_session, user, encryption_key):
        key_cache.set(user.id, encryption_key)
        task = crud.create_task(db_session, user.id, "secret task")
        assert task.content_encrypted is not None
        assert task.content_salt is not None
        assert task.content_version == 1
        # content is decrypted back to plaintext on return
        assert task.content == "secret task"

    def test_plaintext_when_no_key(self, db_session, user):
        key_cache.remove(user.id)
        task = crud.create_task(db_session, user.id, "plain task")
        assert task.content == "plain task"
        assert task.content_encrypted is None

    def test_decrypt_roundtrip(self, db_session, user, encryption_key):
        key_cache.set(user.id, encryption_key)
        task = crud.create_task(db_session, user.id, "roundtrip task")
        decrypted = crud.get_task_decrypted(db_session, user.id, task.id)
        assert decrypted == "roundtrip task"

    def test_decrypt_fallback_to_plaintext(self, db_session, user):
        key_cache.remove(user.id)
        task = crud.create_task(db_session, user.id, "old plaintext task")
        decrypted = crud.get_task_decrypted(db_session, user.id, task.id)
        assert decrypted == "old plaintext task"

    def test_decrypt_returns_none_when_no_key(self, db_session, user, encryption_key):
        key_cache.set(user.id, encryption_key)
        task = crud.create_task(db_session, user.id, "encrypted task")
        key_cache.remove(user.id)
        decrypted = crud.get_task_decrypted(db_session, user.id, task.id)
        assert decrypted is None
