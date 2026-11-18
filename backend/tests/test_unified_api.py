"""Canonical route semantics absorbed from the removed /external API."""

from datetime import date

import app.routers.weekly as weekly_router
from app import crud
from app.auth import create_access_token
from app.envelope import provision_user_dek
from app.key_cache import key_cache
from app.models_token import ApiToken, generate_api_token


def _make_user(db):
    user = crud.create_user(db, "alice", "hash")
    provision_user_dek(db, user)
    return user


def _headers(user):
    token = create_access_token(
        {"sub": str(user.id), "username": user.username, "pwd_ver": user.password_version or 0}
    )
    return {"Authorization": f"Bearer {token}"}


def _token_headers(db, user):
    value = generate_api_token()
    db.add(ApiToken(user_id=user.id, name="t", token=value))
    db.commit()
    return {"X-API-Token": value}


class TestDailyAppend:
    def test_append_joins_with_newline(self, api_env):
        client, db = api_env
        user = _make_user(db)
        h = _headers(user)
        client.post("/api/v1/daily", json={"date": "2026-11-17", "content": "甲"}, headers=h)
        r = client.post(
            "/api/v1/daily",
            json={"date": "2026-11-17", "content": "乙", "append": True},
            headers=h,
        )
        assert r.status_code == 201
        assert r.json()["content"] == "甲\n乙"

    def test_overwrite_is_the_default(self, api_env):
        client, db = api_env
        user = _make_user(db)
        h = _headers(user)
        client.post("/api/v1/daily", json={"date": "2026-11-17", "content": "旧"}, headers=h)
        r = client.post("/api/v1/daily", json={"date": "2026-11-17", "content": "新"}, headers=h)
        assert r.json()["content"] == "新"

    def test_date_defaults_to_today(self, api_env):
        client, db = api_env
        user = _make_user(db)
        r = client.post("/api/v1/daily", json={"content": "无日期"}, headers=_headers(user))
        assert r.status_code == 201
        assert r.json()["date"] == str(date.today())

    def test_append_fails_loudly_when_content_unreadable(self, api_env):
        client, db = api_env
        user = _make_user(db)
        h = _headers(user)
        client.post("/api/v1/daily", json={"date": "2026-11-17", "content": "已加密"}, headers=h)
        key_cache.remove(user.id)  # simulate missing key
        r = client.post(
            "/api/v1/daily",
            json={"date": "2026-11-17", "content": "追加", "append": True},
            headers=h,
        )
        assert r.status_code == 409
        assert r.json()["code"] == "decryption_failed"


class TestWeeklyForce:
    def test_force_false_returns_existing_without_llm(self, api_env, monkeypatch):
        client, db = api_env
        user = _make_user(db)
        h = _headers(user)
        client.post("/api/v1/daily", json={"date": "2026-11-16", "content": "日报"}, headers=h)

        monkeypatch.setattr(weekly_router, "generate_weekly_report", lambda db, entries: "初版")
        first = client.post("/api/v1/weekly/2026-11-16", headers=h)
        assert first.status_code == 200
        assert first.json()["generated"] is True
        assert first.json()["content"] == "初版"

        def must_not_call(*args, **kwargs):
            raise AssertionError("LLM must not be called when force=false and report exists")

        monkeypatch.setattr(weekly_router, "generate_weekly_report", must_not_call)
        second = client.post("/api/v1/weekly/2026-11-16?force=false", headers=h)
        assert second.status_code == 200
        assert second.json()["generated"] is False
        assert second.json()["content"] == "初版"

    def test_force_false_fails_loudly_when_existing_unreadable(self, api_env, monkeypatch):
        client, db = api_env
        user = _make_user(db)
        h = _headers(user)
        client.post("/api/v1/daily", json={"date": "2026-11-16", "content": "日报"}, headers=h)
        monkeypatch.setattr(weekly_router, "generate_weekly_report", lambda db, entries: "初版")
        client.post("/api/v1/weekly/2026-11-16", headers=h)

        key_cache.remove(user.id)  # existing report becomes undecryptable
        r = client.post("/api/v1/weekly/2026-11-16?force=false", headers=h)
        assert r.status_code == 409
        assert r.json()["code"] == "decryption_failed"

    def test_force_true_regenerates(self, api_env, monkeypatch):
        client, db = api_env
        user = _make_user(db)
        h = _headers(user)
        client.post("/api/v1/daily", json={"date": "2026-11-16", "content": "日报"}, headers=h)
        monkeypatch.setattr(weekly_router, "generate_weekly_report", lambda db, entries: "初版")
        client.post("/api/v1/weekly/2026-11-16", headers=h)
        monkeypatch.setattr(weekly_router, "generate_weekly_report", lambda db, entries: "二版")
        r = client.post("/api/v1/weekly/2026-11-16?force=true", headers=h)
        assert r.status_code == 200
        assert r.json()["generated"] is True
        assert r.json()["content"] == "二版"


class TestRemovedExternalRoutes:
    def test_removed_external_get_is_json_404(self, api_env):
        client, db = api_env
        user = _make_user(db)
        r = client.get("/api/v1/external/docs", headers=_headers(user))
        assert r.status_code == 404
        # Must be JSON, never the SPA shell.
        assert r.headers["content-type"].startswith("application/json")

    def test_removed_external_post_is_json_404(self, api_env):
        client, db = api_env
        user = _make_user(db)
        r = client.post("/api/v1/external/daily", json={"content": "x"}, headers=_headers(user))
        assert r.status_code == 404
        assert r.headers["content-type"].startswith("application/json")


class TestTasksPending:
    def test_only_pending_tasks_returned(self, api_env):
        client, db = api_env
        user = _make_user(db)
        h = _headers(user)
        pending = client.post("/api/v1/tasks", json={"content": "待办"}, headers=h).json()
        done = client.post("/api/v1/tasks", json={"content": "已完成"}, headers=h).json()
        client.put(f"/api/v1/tasks/{done['id']}", json={"is_completed": True}, headers=h)

        r = client.get("/api/v1/tasks/pending", headers=h)
        assert r.status_code == 200
        assert [t["id"] for t in r.json()["tasks"]] == [pending["id"]]
        assert r.json()["_decryption_failed"] is False

    def test_pending_works_with_api_token(self, api_env):
        client, db = api_env
        user = _make_user(db)
        h = _token_headers(db, user)
        client.post("/api/v1/tasks", json={"content": "来自 token"}, headers=h)
        r = client.get("/api/v1/tasks/pending", headers=h)
        assert r.status_code == 200
        assert r.json()["tasks"][0]["content"] == "来自 token"
