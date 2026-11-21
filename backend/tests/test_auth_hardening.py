"""Auth hardening: token invalidation, password bytes limit, login throttling."""

import pytest

from app import crud
from app.auth import create_access_token, hash_password, verify_password_safe
from app.envelope import provision_user_dek
from app.routers import auth as auth_router


@pytest.fixture(autouse=True)
def _clear_rate_limit():
    auth_router._attempts.clear()
    yield
    auth_router._attempts.clear()


def _user(db, username="alice", password="Passw0rd1", role="user"):
    user = crud.create_user(db, username, hash_password(password), role=role)
    provision_user_dek(db, user)
    return user


def _jwt(user, *, with_pwd_ver=True):
    payload = {"sub": str(user.id), "username": user.username}
    if with_pwd_ver:
        payload["pwd_ver"] = user.password_version or 0
    return {"Authorization": "Bearer " + create_access_token(payload)}


class TestPasswordVersion:
    def test_old_token_rejected_after_change(self, api_env):
        client, db = api_env
        user = _user(db)
        old_headers = _jwt(user)

        new_token = client.post(
            "/api/v1/auth/change-password",
            headers=old_headers,
            json={"old_password": "Passw0rd1", "new_password": "NewPassw0rd9"},
        ).json()["access_token"]

        assert client.get("/api/v1/daily", headers=old_headers).status_code == 401
        assert (
            client.get(
                "/api/v1/daily", headers={"Authorization": f"Bearer {new_token}"}
            ).status_code
            == 200
        )

    def test_token_without_pwd_ver_is_invalidated_too(self, api_env):
        """Regression: a missing pwd_ver claim must not be a permanent bypass."""
        client, db = api_env
        user = _user(db)
        legacy_headers = _jwt(user, with_pwd_ver=False)

        assert client.get("/api/v1/daily", headers=legacy_headers).status_code == 200

        crud.change_password(db, user, hash_password("Other0Pass"))

        assert client.get("/api/v1/daily", headers=legacy_headers).status_code == 401


class TestPasswordLength:
    def test_multibyte_password_over_72_bytes_rejected(self, api_env):
        client, db = api_env
        user = _user(db)

        response = client.post(
            "/api/v1/auth/change-password",
            headers=_jwt(user),
            json={"old_password": "Passw0rd1", "new_password": "密" * 25 + "a1"},
        )

        assert response.status_code == 400
        assert "72" in response.json()["detail"]

    def test_verify_password_safe_handles_unknown_user(self):
        assert verify_password_safe("whatever", None) is False


class TestLoginThrottle:
    def test_failures_lock_the_account_window(self, api_env):
        client, db = api_env
        _user(db)

        for _ in range(auth_router._MAX_ATTEMPTS):
            assert (
                client.post(
                    "/api/v1/auth/login",
                    json={"username": "alice", "password": "wrong-pass-1"},
                ).status_code
                == 401
            )

        blocked = client.post(
            "/api/v1/auth/login", json={"username": "alice", "password": "Passw0rd1"}
        )

        assert blocked.status_code == 429

    def test_successful_logins_do_not_consume_the_quota(self, api_env):
        client, db = api_env
        _user(db)

        for _ in range(auth_router._MAX_ATTEMPTS + 2):
            response = client.post(
                "/api/v1/auth/login", json={"username": "alice", "password": "Passw0rd1"}
            )
            assert response.status_code == 200


class TestSetup:
    def test_second_setup_is_rejected(self, api_env):
        client, _db = api_env

        first = client.post(
            "/api/v1/auth/setup", json={"username": "admin", "password": "Passw0rd1"}
        )
        second = client.post(
            "/api/v1/auth/setup", json={"username": "intruder", "password": "Passw0rd1"}
        )

        assert first.status_code == 200
        assert second.status_code == 400
        assert second.json()["detail"] == "Setup has already been completed"

    def test_first_setup_creates_admin_with_working_key(self, api_env):
        client, _db = api_env

        payload = client.post(
            "/api/v1/auth/setup", json={"username": "admin", "password": "Passw0rd1"}
        ).json()
        headers = {"Authorization": f"Bearer {payload['access_token']}"}

        me = client.get("/api/v1/users/me", headers=headers).json()
        assert me["role"] == "admin"

        written = client.post(
            "/api/v1/daily", headers=headers, json={"date": "2026-11-17", "content": "hello"}
        )
        assert written.status_code == 201


class TestUsernameNormalization:
    def test_login_ignores_surrounding_whitespace(self, api_env):
        client, db = api_env
        _user(db, username="alice")

        response = client.post(
            "/api/v1/auth/login", json={"username": "  alice  ", "password": "Passw0rd1"}
        )

        assert response.status_code == 200

    def test_admin_created_username_is_trimmed(self, api_env):
        client, db = api_env
        admin = _user(db, username="admin", role="admin")

        created = client.post(
            "/api/v1/users",
            headers=_jwt(admin),
            json={"username": "  bob  ", "password": "Passw0rd1"},
        )

        assert created.status_code == 201
        assert created.json()["username"] == "bob"


class TestSetupIsNotABcryptSink:
    def test_second_setup_rejects_before_password_validation(self, api_env):
        """Once an account exists, /auth/setup must not hash the supplied password."""
        client, _db = api_env
        client.post("/api/v1/auth/setup", json={"username": "admin", "password": "Passw0rd1"})

        # Passes the schema but would fail validate_password (no digit): the
        # early guard must win, so no bcrypt hash is spent on this request.
        second = client.post(
            "/api/v1/auth/setup", json={"username": "intruder", "password": "allletters"}
        )

        assert second.status_code == 400
        assert second.json()["detail"] == "Setup has already been completed"
