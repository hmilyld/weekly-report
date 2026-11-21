"""End-to-end flow after the router/response-model refactor.

Covers the path a real client takes: setup → daily → weekly → monthly → read back,
with the LLM replaced by a stub (no network).
"""

from datetime import date

from app import crud
from app.key_cache import key_cache
from app.routers import monthly as monthly_router
from app.routers import weekly as weekly_router


def _setup_admin(client):
    token = client.post(
        "/api/v1/auth/setup", json={"username": "admin", "password": "Passw0rd1"}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


class TestFullFlow:
    def test_setup_daily_weekly_monthly(self, api_env, monkeypatch):
        client, db = api_env
        headers = _setup_admin(client)

        assert (
            client.post(
                "/api/v1/daily", headers=headers, json={"date": "2026-11-16", "content": "周一"}
            ).status_code
            == 201
        )
        assert (
            client.post(
                "/api/v1/daily", headers=headers, json={"date": "2026-11-17", "content": "周二"}
            ).status_code
            == 201
        )

        monkeypatch.setattr(weekly_router, "generate_weekly_report", lambda db, entries: "周报正文")
        weekly = client.post("/api/v1/weekly/2026-11-16", headers=headers)
        assert weekly.status_code == 200
        assert weekly.json()["content"] == "周报正文"
        assert weekly.json()["generated"] is True

        monkeypatch.setattr(
            monthly_router, "generate_monthly_report", lambda db, entries: "月报正文"
        )
        monthly = client.post("/api/v1/monthly/2026/11", headers=headers)
        assert monthly.status_code == 200
        assert monthly.json()["content"] == "月报正文"

        # Read back through the list/detail endpoints (response models).
        assert [
            r["content"] for r in client.get("/api/v1/daily", headers=headers).json()["reports"]
        ] == [
            "周一",
            "周二",
        ]
        assert (
            client.get("/api/v1/weekly", headers=headers).json()["reports"][0]["content"]
            == "周报正文"
        )
        assert (
            client.get("/api/v1/weekly/2026-11-16", headers=headers).json()["content"] == "周报正文"
        )
        assert (
            client.get("/api/v1/monthly/2026/11", headers=headers).json()["content"] == "月报正文"
        )

        # Ciphertext at rest, plaintext only in the response.
        user = crud.get_user_by_username(db, "admin")
        row = crud.get_daily_report(db, user.id, date(2026, 11, 16))
        assert row.content_encrypted
        assert row.content == ""

    def test_weekly_edit_and_monthly_edit(self, api_env, monkeypatch):
        client, _db = api_env
        headers = _setup_admin(client)
        client.post(
            "/api/v1/daily", headers=headers, json={"date": "2026-11-16", "content": "周一"}
        )
        monkeypatch.setattr(weekly_router, "generate_weekly_report", lambda db, entries: "初版")
        monkeypatch.setattr(monthly_router, "generate_monthly_report", lambda db, entries: "初版")
        client.post("/api/v1/weekly/2026-11-16", headers=headers)
        client.post("/api/v1/monthly/2026/11", headers=headers)

        weekly = client.put(
            "/api/v1/weekly/2026-11-16", headers=headers, json={"content": "手改周报"}
        )
        monthly = client.put(
            "/api/v1/monthly/2026/11", headers=headers, json={"content": "手改月报"}
        )

        assert weekly.status_code == 200 and weekly.json()["content"] == "手改周报"
        assert monthly.status_code == 200 and monthly.json()["content"] == "手改月报"

    def test_unreadable_content_is_flagged_not_empty(self, api_env, monkeypatch):
        client, db = api_env
        headers = _setup_admin(client)
        client.post(
            "/api/v1/daily", headers=headers, json={"date": "2026-11-16", "content": "周一"}
        )
        user = crud.get_user_by_username(db, "admin")

        key_cache.remove(user.id)  # simulate a missing DEK at read time

        payload = client.get("/api/v1/daily", headers=headers).json()

        assert payload["_decryption_failed"] is True
        assert payload["reports"][0]["_decryption_failed"] is True
        assert payload["reports"][0]["content"] == ""
