"""API token lifecycle: revoking all tokens of the current user."""

from app import crud
from app.auth import create_access_token, hash_password
from app.envelope import provision_user_dek
from app.models_token import ApiToken, generate_api_token


def _token_user(db, username):
    user = crud.create_user(db, username, hash_password("Passw0rd1"))
    provision_user_dek(db, user)
    headers = {
        "Authorization": "Bearer "
        + create_access_token(
            {"sub": str(user.id), "username": user.username, "pwd_ver": user.password_version or 0}
        )
    }
    return user, headers


def _issue(db, user, name="script"):
    value = generate_api_token()
    db.add(ApiToken(user_id=user.id, name=name, token=value))
    db.commit()
    return value


class TestRevokeAllTokens:
    def test_revokes_every_token_of_the_caller(self, api_env):
        client, db = api_env
        user, headers = _token_user(db, "alice")
        first = _issue(db, user, "phone")
        second = _issue(db, user, "laptop")

        response = client.delete("/api/v1/tokens", headers=headers)

        assert response.status_code == 200
        assert response.json() == {"revoked": 2}
        assert client.get("/api/v1/daily", headers={"X-API-Token": first}).status_code == 401
        assert client.get("/api/v1/daily", headers={"X-API-Token": second}).status_code == 401
        assert client.get("/api/v1/tokens", headers=headers).json() == []

    def test_leaves_other_users_tokens_alone(self, api_env):
        client, db = api_env
        alice, alice_headers = _token_user(db, "alice")
        bob, _ = _token_user(db, "bob")
        _issue(db, alice)
        bob_token = _issue(db, bob)

        client.delete("/api/v1/tokens", headers=alice_headers)

        assert client.get("/api/v1/daily", headers={"X-API-Token": bob_token}).status_code == 200

    def test_requires_jwt_not_api_token(self, api_env):
        client, db = api_env
        user, _ = _token_user(db, "alice")
        token = _issue(db, user)

        response = client.delete("/api/v1/tokens", headers={"X-API-Token": token})

        assert response.status_code == 401
        assert client.get("/api/v1/daily", headers={"X-API-Token": token}).status_code == 200
