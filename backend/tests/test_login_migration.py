"""Router-level tests: envelope migration must never lock the account out."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import main
from app import crud
from app.auth import hash_password
from app.database import get_db
from app.key_cache import key_cache
from app.models import Base


@pytest.fixture()
def client_and_db():
    # StaticPool: one shared connection across threads — TestClient runs
    # endpoints in a worker thread, and :memory: is per-connection.
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()

    def override_get_db():
        yield session

    main.app.dependency_overrides[get_db] = override_get_db
    # No context manager: endpoints only, lifespan (startup migrations) not run.
    client = TestClient(main.app)
    yield client, session
    main.app.dependency_overrides.clear()
    session.close()
    key_cache.clear()


class TestLoginMigration:
    def test_migration_failure_still_returns_token(self, client_and_db, monkeypatch):
        client, db = client_and_db
        crud.create_user(db, "legacy", hash_password("Passw0rd1"))

        def boom(*args, **kwargs):
            raise RuntimeError("simulated undecryptable legacy row")

        monkeypatch.setattr("app.routers.auth.migrate_user_to_dek", boom)
        r = client.post("/api/v1/auth/login", json={"username": "legacy", "password": "Passw0rd1"})
        assert r.status_code == 200
        assert r.json()["access_token"]
        # wrapped_dek stays NULL → the next login retries the migration.
        user = crud.get_user_by_username(db, "legacy")
        assert user.wrapped_dek is None

    def test_successful_login_migrates_legacy_user(self, client_and_db):
        client, db = client_and_db
        crud.create_user(db, "legacy", hash_password("Passw0rd1"))
        r = client.post("/api/v1/auth/login", json={"username": "legacy", "password": "Passw0rd1"})
        assert r.status_code == 200
        user = crud.get_user_by_username(db, "legacy")
        assert user.wrapped_dek is not None
        assert key_cache.get(user.id) is not None

    def test_wrong_password_still_401(self, client_and_db):
        client, db = client_and_db
        crud.create_user(db, "legacy", hash_password("Passw0rd1"))
        r = client.post(
            "/api/v1/auth/login", json={"username": "legacy", "password": "WrongPass999"}
        )
        assert r.status_code == 401
