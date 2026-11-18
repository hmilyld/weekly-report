"""Tests for the one-time legacy → DEK migration and its safety properties."""

import base64
import hashlib
import os
from datetime import date

import pytest
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import crud
from app.auth import derive_user_key
from app.crypto import encrypt_content
from app.encryption_utils import (
    ContentDecryptionError,
    decrypt_daily_entries,
    set_encrypted_content,
)
from app.envelope import unwrap_dek
from app.key_cache import key_cache
from app.migration import migrate_app_config_secret, migrate_user_to_dek
from app.models import AppConfig, Base, DailyReport, MonthlyReport, Task, WeeklyReport

PASSWORD = "LegacyPass123"


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
    return crud.create_user(db_session, "legacyuser", "hash123")


@pytest.fixture()
def legacy_key(user):
    return derive_user_key(PASSWORD, user)


def _seed_legacy_data(db, user, legacy_key):
    """One record per legacy format, across all four content tables."""
    # 1. Plaintext (written via API token before any login)
    db.add(DailyReport(user_id=user.id, date=date(2025, 1, 6), content="plaintext daily"))
    # 2. Legacy v1, tag separated
    enc = encrypt_content("legacy weekly", legacy_key)
    db.add(
        WeeklyReport(
            user_id=user.id,
            week_start=date(2025, 1, 6),
            week_end=date(2025, 1, 12),
            content="",
            content_encrypted=enc["ciphertext"],
            content_nonce=enc["nonce"],
            content_tag=enc["tag"],
            content_version=1,
        )
    )
    # 3. Legacy v1, OLD format: GCM tag embedded in ciphertext, tag column empty
    nonce = os.urandom(12)
    ct_with_tag = AESGCM(legacy_key).encrypt(nonce, b"old format monthly", None)
    db.add(
        MonthlyReport(
            user_id=user.id,
            year=2025,
            month=1,
            content="",
            content_encrypted=base64.b64encode(ct_with_tag).decode(),
            content_nonce=base64.b64encode(nonce).decode(),
            content_tag="",
            content_version=1,
        )
    )
    # 4. Plaintext task
    db.add(Task(user_id=user.id, content="plaintext task"))
    db.commit()


class TestMigrateUserToDek:
    def test_migrates_all_formats(self, db_session, user, legacy_key):
        _seed_legacy_data(db_session, user, legacy_key)
        dek = migrate_user_to_dek(db_session, user, PASSWORD)

        assert len(dek) == 32
        assert user.wrapped_dek is not None
        assert unwrap_dek(user.wrapped_dek, user.id) == dek
        assert user.needs_encryption_migration is False
        assert key_cache.get(user.id) == dek

        daily = crud.get_daily_report(db_session, user.id, date(2025, 1, 6))
        weekly = crud.get_weekly_report(db_session, user.id, date(2025, 1, 6))
        monthly = crud.get_monthly_report(db_session, user.id, 2025, 1)
        task = crud.get_tasks(db_session, user.id)[0]

        # get_daily_report returns the raw row; use the decrypting accessor.
        assert (
            crud.get_daily_report_decrypted(db_session, user.id, date(2025, 1, 6))
            == "plaintext daily"
        )
        assert weekly.content == "legacy weekly"
        assert monthly.content == "old format monthly"
        assert task.content == "plaintext task"
        for record in (daily, weekly, monthly, task):
            assert record.content_version == 2
            assert record.content_salt is None
        db_session.expire_all()
        for model, pk in (
            (DailyReport, daily.id),
            (WeeklyReport, weekly.id),
            (MonthlyReport, monthly.id),
            (Task, task.id),
        ):
            row = db_session.get(model, pk)
            # Plaintext column must be empty at rest
            assert row.content == ""
            assert row.content_encrypted

    def test_idempotent(self, db_session, user, legacy_key):
        _seed_legacy_data(db_session, user, legacy_key)
        dek1 = migrate_user_to_dek(db_session, user, PASSWORD)
        before = _ciphertext_snapshot(db_session, user)
        # Second call (even with a different password) is a no-op.
        dek2 = migrate_user_to_dek(db_session, user, "WhateverElse456")
        assert dek1 == dek2
        assert _ciphertext_snapshot(db_session, user) == before

    def test_failure_rolls_back_everything(self, db_session, user, legacy_key):
        _seed_legacy_data(db_session, user, legacy_key)
        before = _ciphertext_snapshot(db_session, user)
        # The error must identify the failing record for operator repair.
        with pytest.raises(ContentDecryptionError, match="weekly_reports"):
            migrate_user_to_dek(db_session, user, "WrongPassword789")
        db_session.expire_all()
        user = crud.get_user_by_username(db_session, "legacyuser")
        assert user.wrapped_dek is None  # retry possible on next login
        assert _ciphertext_snapshot(db_session, user) == before

    def test_empty_user_migrates_cleanly(self, db_session, user):
        dek = migrate_user_to_dek(db_session, user, PASSWORD)
        assert user.wrapped_dek is not None
        assert key_cache.get(user.id) == dek


def _ciphertext_snapshot(db, user):
    snapshot = {}
    for model in (DailyReport, WeeklyReport, MonthlyReport, Task):
        for row in db.query(model).filter(model.user_id == user.id).all():
            snapshot[(model.__tablename__, row.id)] = (
                row.content,
                row.content_encrypted,
                row.content_nonce,
                row.content_tag,
                row.content_version,
            )
    return snapshot


class TestPasswordChangeDecoupled:
    def test_password_change_never_touches_ciphertext(self, db_session, user, legacy_key):
        _seed_legacy_data(db_session, user, legacy_key)
        migrate_user_to_dek(db_session, user, PASSWORD)
        before = _ciphertext_snapshot(db_session, user)

        crud.change_password(db_session, user, "new-hash")

        assert user.password_version == 1
        assert _ciphertext_snapshot(db_session, user) == before
        # Same DEK still decrypts everything after the password change.
        assert (
            crud.get_daily_report_decrypted(db_session, user.id, date(2025, 1, 6))
            == "plaintext daily"
        )


class TestLegacyKdfFrozen:
    def test_derive_user_key_matches_historical_parameters(self, user):
        """Byte-level lock: legacy ciphertext depends on these exact parameters."""
        salt = f"user_{user.id}_encryption_salt".encode().ljust(32, b"\0")[:32]
        expected = hashlib.pbkdf2_hmac("sha256", PASSWORD.encode(), salt, 100_000, dklen=32)
        assert derive_user_key(PASSWORD, user) == expected


class TestGenerationFailsLoudly:
    def test_missing_key_raises_instead_of_dropping_entries(self, db_session, user, legacy_key):
        _seed_legacy_data(db_session, user, legacy_key)
        migrate_user_to_dek(db_session, user, PASSWORD)
        dailies = crud.get_daily_reports_by_week(db_session, user.id, date(2025, 1, 6))
        key_cache.remove(user.id)
        with pytest.raises(ContentDecryptionError):
            decrypt_daily_entries(dailies, user.id)

    def test_partial_decryption_failure_raises(self, db_session, user, legacy_key):
        _seed_legacy_data(db_session, user, legacy_key)
        migrate_user_to_dek(db_session, user, PASSWORD)
        # Add a second daily whose ciphertext is corrupted.
        daily = DailyReport(user_id=user.id, date=date(2025, 1, 7), content="")
        set_encrypted_content(daily, "will be corrupted", user.id, key_cache.get(user.id))
        raw = bytearray(base64.b64decode(daily.content_encrypted))
        raw[0] ^= 0xFF
        daily.content_encrypted = base64.b64encode(bytes(raw)).decode()
        db_session.add(daily)
        db_session.commit()
        dailies = crud.get_daily_reports_by_week(db_session, user.id, date(2025, 1, 6))
        with pytest.raises(ContentDecryptionError):
            decrypt_daily_entries(dailies, user.id)


class TestAppConfigSecretMigration:
    def test_legacy_api_key_rewrapped(self, db_session):
        enc = encrypt_content("sk-legacy-llm", crud._get_legacy_api_key_encryption_key())
        legacy = base64.b64encode(
            f"{enc['ciphertext']}:{enc['nonce']}:{enc['tag']}".encode()
        ).decode()
        db_session.add(AppConfig(id=1, api_key=legacy))
        db_session.commit()

        migrate_app_config_secret(db_session)

        config = db_session.get(AppConfig, 1)
        assert config.api_key.startswith("ek1:")
        assert crud.decrypt_api_key(config.api_key) == "sk-legacy-llm"
        # Idempotent
        migrate_app_config_secret(db_session)
        assert crud.decrypt_api_key(config.api_key) == "sk-legacy-llm"

    def test_undecryptable_legacy_key_left_untouched(self, db_session):
        # Looks like the legacy format but was encrypted with another JWT secret.
        other_key = hashlib.pbkdf2_hmac("sha256", b"other-secret", b"salt", 1000, dklen=32)
        enc = encrypt_content("sk-lost", other_key)
        legacy = base64.b64encode(
            f"{enc['ciphertext']}:{enc['nonce']}:{enc['tag']}".encode()
        ).decode()
        db_session.add(AppConfig(id=1, api_key=legacy))
        db_session.commit()

        migrate_app_config_secret(db_session)

        config = db_session.get(AppConfig, 1)
        assert config.api_key == legacy  # unchanged, repairable via Settings
