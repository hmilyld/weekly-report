"""Wire contract: the JSON keys documented for clients must not drift."""

from app import crud
from app.auth import create_access_token, hash_password
from app.envelope import provision_user_dek


def _auth(client, db):
    user = crud.create_user(db, "alice", hash_password("Passw0rd1"), role="admin")
    provision_user_dek(db, user)
    token = create_access_token(
        {"sub": str(user.id), "username": user.username, "pwd_ver": user.password_version or 0}
    )
    return {"Authorization": f"Bearer {token}"}


class TestListContracts:
    def test_daily_list_keys(self, api_env):
        client, db = api_env
        headers = _auth(client, db)
        client.post("/api/v1/daily", headers=headers, json={"date": "2026-11-17", "content": "x"})

        payload = client.get("/api/v1/daily", headers=headers).json()

        assert set(payload) == {"reports", "_decryption_failed"}
        assert set(payload["reports"][0]) == {
            "id",
            "date",
            "content",
            "created_at",
            "updated_at",
            "_decryption_failed",
        }

    def test_task_list_keys(self, api_env):
        client, db = api_env
        headers = _auth(client, db)
        client.post("/api/v1/tasks", headers=headers, json={"content": "t"})

        payload = client.get("/api/v1/tasks", headers=headers).json()

        assert set(payload) == {"tasks", "_decryption_failed"}
        assert set(payload["tasks"][0]) == {
            "id",
            "user_id",
            "content",
            "deadline",
            "is_completed",
            "created_at",
            "updated_at",
            "_decryption_failed",
        }

    def test_completed_list_has_pagination(self, api_env):
        client, db = api_env
        headers = _auth(client, db)

        payload = client.get("/api/v1/tasks/completed", headers=headers).json()

        assert set(payload) == {"tasks", "total", "offset", "limit", "_decryption_failed"}

    def test_weekly_and_monthly_list_keys(self, api_env):
        client, db = api_env
        headers = _auth(client, db)

        assert set(client.get("/api/v1/weekly", headers=headers).json()) == {
            "reports",
            "_decryption_failed",
        }
        assert set(client.get("/api/v1/monthly", headers=headers).json()) == {
            "reports",
            "_decryption_failed",
        }

    def test_openapi_documents_list_endpoints(self, api_env):
        client, _db = api_env
        schema = client.get("/openapi.json").json()
        responses = schema["paths"]["/api/v1/daily"]["get"]["responses"]["200"]
        assert responses["content"]["application/json"]["schema"]["$ref"].endswith(
            "DailyReportListResponse"
        )
        # The SPA catch-all must not leak into the published contract.
        assert not any(path.startswith("/{full_path") for path in schema["paths"])
