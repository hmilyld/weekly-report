"""Admin-only user management: role guards, conflicts and cascade deletion."""

from datetime import date

from app import crud
from app.auth import create_access_token
from app.envelope import provision_user_dek
from app.models import ApiToken, DailyReport, Task, generate_api_token


def make_user(db, username, role="user"):
    user = crud.create_user(db, username, "hash", role=role)
    provision_user_dek(db, user)
    return user


def headers_for(user):
    token = create_access_token(
        {"sub": str(user.id), "username": user.username, "pwd_ver": user.password_version or 0}
    )
    return {"Authorization": f"Bearer {token}"}


def test_me_returns_the_caller(api_env):
    client, db = api_env
    user = make_user(db, "alice")

    response = client.get("/api/v1/users/me", headers=headers_for(user))

    assert response.status_code == 200
    assert response.json()["username"] == "alice"
    assert response.json()["role"] == "user"


class TestListUsers:
    def test_admin_sees_every_user_without_secrets(self, api_env):
        client, db = api_env
        admin = make_user(db, "admin", role="admin")
        make_user(db, "bob")

        response = client.get("/api/v1/users", headers=headers_for(admin))

        assert response.status_code == 200
        users = response.json()["users"]
        assert {u["username"] for u in users} == {"admin", "bob"}
        assert all("password_hash" not in u and "wrapped_dek" not in u for u in users)

    def test_regular_user_is_forbidden(self, api_env):
        client, db = api_env
        user = make_user(db, "bob")

        assert client.get("/api/v1/users", headers=headers_for(user)).status_code == 403

    def test_missing_credentials_are_rejected(self, api_env):
        client, _db = api_env
        assert client.get("/api/v1/users").status_code == 401


class TestCreateUser:
    def test_admin_creates_a_user_with_a_wrapped_key(self, api_env):
        client, db = api_env
        admin = make_user(db, "admin", role="admin")

        response = client.post(
            "/api/v1/users",
            json={"username": "carol", "password": "Passw0rd1"},
            headers=headers_for(admin),
        )

        assert response.status_code == 201
        assert response.json()["role"] == "user"
        created = crud.get_user_by_username(db, "carol")
        assert created.wrapped_dek is not None

    def test_duplicate_username_conflicts(self, api_env):
        client, db = api_env
        admin = make_user(db, "admin", role="admin")

        response = client.post(
            "/api/v1/users",
            json={"username": "admin", "password": "Passw0rd1"},
            headers=headers_for(admin),
        )

        assert response.status_code == 409

    def test_blank_username_is_rejected(self, api_env):
        client, db = api_env
        admin = make_user(db, "admin", role="admin")

        response = client.post(
            "/api/v1/users",
            json={"username": "   ", "password": "Passw0rd1"},
            headers=headers_for(admin),
        )

        assert response.status_code == 400

    def test_password_without_digit_is_rejected(self, api_env):
        client, db = api_env
        admin = make_user(db, "admin", role="admin")

        response = client.post(
            "/api/v1/users",
            json={"username": "dave", "password": "allletters"},
            headers=headers_for(admin),
        )

        assert response.status_code == 400

    def test_invalid_role_fails_validation(self, api_env):
        client, db = api_env
        admin = make_user(db, "admin", role="admin")

        response = client.post(
            "/api/v1/users",
            json={"username": "erin", "password": "Passw0rd1", "role": "owner"},
            headers=headers_for(admin),
        )

        assert response.status_code == 422

    def test_regular_user_cannot_create(self, api_env):
        client, db = api_env
        user = make_user(db, "bob")

        response = client.post(
            "/api/v1/users",
            json={"username": "carol", "password": "Passw0rd1"},
            headers=headers_for(user),
        )

        assert response.status_code == 403


class TestDeleteUser:
    def test_admin_cannot_delete_themselves(self, api_env):
        client, db = api_env
        admin = make_user(db, "admin", role="admin")

        response = client.delete(f"/api/v1/users/{admin.id}", headers=headers_for(admin))

        assert response.status_code == 400

    def test_unknown_user_is_not_found(self, api_env):
        client, db = api_env
        admin = make_user(db, "admin", role="admin")

        response = client.delete("/api/v1/users/9999", headers=headers_for(admin))

        assert response.status_code == 404

    def test_deleting_a_user_removes_all_of_their_data(self, api_env):
        client, db = api_env
        admin = make_user(db, "admin", role="admin")
        victim = make_user(db, "bob")

        db.add(DailyReport(user_id=victim.id, date=date(2026, 11, 16), content="日报"))
        db.add(Task(user_id=victim.id, content="待办"))
        db.add(ApiToken(user_id=victim.id, name="t", token=generate_api_token()))
        db.commit()

        response = client.delete(f"/api/v1/users/{victim.id}", headers=headers_for(admin))

        assert response.status_code == 204
        assert crud.get_user_by_username(db, "bob") is None
        assert db.query(DailyReport).filter(DailyReport.user_id == victim.id).count() == 0
        assert db.query(Task).filter(Task.user_id == victim.id).count() == 0
        assert db.query(ApiToken).filter(ApiToken.user_id == victim.id).count() == 0


class TestUpdateRole:
    def test_admin_promotes_another_user(self, api_env):
        client, db = api_env
        admin = make_user(db, "admin", role="admin")
        bob = make_user(db, "bob")

        response = client.put(
            f"/api/v1/users/{bob.id}/role",
            json={"role": "admin"},
            headers=headers_for(admin),
        )

        assert response.status_code == 200
        assert response.json()["role"] == "admin"

    def test_admin_cannot_change_their_own_role(self, api_env):
        client, db = api_env
        admin = make_user(db, "admin", role="admin")

        response = client.put(
            f"/api/v1/users/{admin.id}/role",
            json={"role": "user"},
            headers=headers_for(admin),
        )

        assert response.status_code == 400

    def test_unknown_user_is_not_found(self, api_env):
        client, db = api_env
        admin = make_user(db, "admin", role="admin")

        response = client.put(
            "/api/v1/users/9999/role",
            json={"role": "admin"},
            headers=headers_for(admin),
        )

        assert response.status_code == 404

    def test_invalid_role_fails_validation(self, api_env):
        client, db = api_env
        admin = make_user(db, "admin", role="admin")
        bob = make_user(db, "bob")

        response = client.put(
            f"/api/v1/users/{bob.id}/role",
            json={"role": "root"},
            headers=headers_for(admin),
        )

        assert response.status_code == 422
