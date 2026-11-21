"""LLM config API: the stored API key must never leave the server in plaintext."""

from app import crud
from app.auth import create_access_token, hash_password
from app.envelope import provision_user_dek

SECRET = "sk-real-secret-value-1234567890"


def _admin(client, db):
    user = crud.create_user(db, "admin", hash_password("Passw0rd1"), role="admin")
    provision_user_dek(db, user)
    token = create_access_token(
        {"sub": str(user.id), "username": user.username, "pwd_ver": user.password_version or 0}
    )
    return user, {"Authorization": f"Bearer {token}"}


def _seed(db):
    crud.update_app_config(
        db,
        llm_api_url="https://api.example.com/v1/chat/completions",
        llm_model_name="model-a",
        api_key=SECRET,
    )


class TestApiKeyMasking:
    def test_get_masks_key(self, api_env):
        client, db = api_env
        _, headers = _admin(client, db)
        _seed(db)

        payload = client.get("/api/v1/config", headers=headers).json()

        assert payload["api_key"] != SECRET
        assert "*" in payload["api_key"]

    def test_put_does_not_return_plaintext_key(self, api_env):
        client, db = api_env
        _, headers = _admin(client, db)
        _seed(db)

        payload = client.put(
            "/api/v1/config", headers=headers, json={"llm_model_name": "model-b"}
        ).json()

        assert payload["llm_model_name"] == "model-b"
        assert payload["api_key"] != SECRET
        assert "*" in payload["api_key"]

    def test_put_with_masked_value_keeps_stored_key(self, api_env):
        client, db = api_env
        _, headers = _admin(client, db)
        _seed(db)
        masked = client.get("/api/v1/config", headers=headers).json()["api_key"]

        client.put("/api/v1/config", headers=headers, json={"api_key": masked})

        db.expire_all()
        assert crud.get_app_config(db).api_key == SECRET

    def test_short_key_is_masked_too(self, api_env):
        client, db = api_env
        _, headers = _admin(client, db)
        crud.update_app_config(db, api_key="sk-1234")

        payload = client.get("/api/v1/config", headers=headers).json()

        assert payload["api_key"] == "********"

    def test_key_containing_asterisk_can_be_saved(self, api_env):
        """A real key with '*' is only ambiguous on the wire, not in storage."""
        client, db = api_env
        _, headers = _admin(client, db)
        real = "sk-a*b-c-1234567890"

        client.put("/api/v1/config", headers=headers, json={"api_key": real})

        db.expire_all()
        assert crud.get_app_config(db).api_key == real
