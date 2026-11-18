"""Tests for envelope encryption: KEK derivation, DEK wrapping, startup load."""

import base64

import pytest
from cryptography.exceptions import InvalidTag
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import crud, envelope
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
    return crud.create_user(db_session, "alice", "hash123")


class TestKek:
    def test_kek_is_deterministic_and_32_bytes(self):
        kek1 = envelope.get_kek()
        kek2 = envelope.get_kek()
        assert kek1 == kek2
        assert len(kek1) == 32

    def test_kek_differs_from_master_key(self):
        master = base64.b64decode(envelope.settings.encryption_master_key)
        assert envelope.get_kek() != master

    def test_invalid_base64_rejected(self, monkeypatch):
        monkeypatch.setattr(envelope.settings, "encryption_master_key", "not-base64!!")
        monkeypatch.setattr(envelope, "_kek", None)
        with pytest.raises(RuntimeError, match="base64"):
            envelope.get_kek()

    def test_wrong_length_rejected(self, monkeypatch):
        monkeypatch.setattr(
            envelope.settings, "encryption_master_key", base64.b64encode(b"short").decode()
        )
        monkeypatch.setattr(envelope, "_kek", None)
        with pytest.raises(RuntimeError, match="32 bytes"):
            envelope.get_kek()


class TestDekWrapping:
    def test_wrap_unwrap_roundtrip(self, user):
        dek = b"\x01" * 32
        wrapped = envelope.wrap_dek(dek, user.id)
        assert envelope.unwrap_dek(wrapped, user.id) == dek

    def test_aad_binds_user_identity(self, user):
        dek = b"\x02" * 32
        wrapped = envelope.wrap_dek(dek, user.id)
        # A wrapped DEK must not be usable for another account.
        with pytest.raises(InvalidTag):
            envelope.unwrap_dek(wrapped, user.id + 1)

    def test_tampered_wrapped_dek_fails(self, user):
        wrapped = envelope.wrap_dek(b"\x03" * 32, user.id)
        raw = bytearray(base64.b64decode(wrapped))
        raw[-1] ^= 0xFF
        with pytest.raises(InvalidTag):
            envelope.unwrap_dek(base64.b64encode(bytes(raw)).decode(), user.id)

    def test_wrong_dek_length_rejected(self, user):
        with pytest.raises(ValueError):
            envelope.wrap_dek(b"too-short", user.id)

    def test_truncated_wrapped_dek_rejected(self, user):
        with pytest.raises(ValueError):
            envelope.unwrap_dek(base64.b64encode(b"tiny").decode(), user.id)


class TestProvisionAndStartupLoad:
    def test_provision_stores_wrapped_dek(self, db_session, user):
        dek = envelope.provision_user_dek(db_session, user)
        assert len(dek) == 32
        assert user.wrapped_dek is not None
        assert user.wrapped_dek_version == 1
        assert user.needs_encryption_migration is False
        assert key_cache.get(user.id) == dek

    def test_restart_restores_keys_from_db(self, db_session, user):
        dek = envelope.provision_user_dek(db_session, user)
        # Simulate a process restart: cache emptied, fresh DB session.
        key_cache.clear()
        engine = db_session.get_bind()
        fresh_session = sessionmaker(bind=engine)()
        try:
            failed = envelope.load_all_user_deks(fresh_session)
            assert failed == []
            assert key_cache.get(user.id) == dek
        finally:
            fresh_session.close()

    def test_unmigrated_user_not_loaded(self, db_session, user):
        # wrapped_dek is NULL → nothing to load, no failure reported.
        key_cache.clear()
        assert envelope.load_all_user_deks(db_session) == []
        assert key_cache.get(user.id) is None
        assert envelope.ensure_user_dek(db_session, user) is None

    def test_corrupted_wrapped_dek_reported_per_user(self, db_session, user):
        envelope.provision_user_dek(db_session, user)
        user.wrapped_dek = base64.b64encode(b"\x00" * 60).decode()
        db_session.commit()
        key_cache.clear()
        failed = envelope.load_all_user_deks(db_session)
        assert failed == [user.id]
        assert key_cache.get(user.id) is None

    def test_ensure_user_dek_unwraps_on_demand(self, db_session, user):
        dek = envelope.provision_user_dek(db_session, user)
        key_cache.remove(user.id)
        assert envelope.ensure_user_dek(db_session, user) == dek
        assert key_cache.get(user.id) == dek


class TestConfigSecret:
    def test_wrap_unwrap_roundtrip(self):
        stored = envelope.wrap_config_secret("sk-secret-key")
        assert stored.startswith(envelope.CONFIG_SECRET_PREFIX)
        assert envelope.unwrap_config_secret(stored) == "sk-secret-key"

    def test_unwrap_rejects_unmarked_value(self):
        with pytest.raises(ValueError):
            envelope.unwrap_config_secret("sk-not-wrapped")
