"""Unified auth: data routes accept JWT or X-API-Token; admin stays JWT-only."""

from datetime import UTC, date, datetime, timedelta

from app import crud
from app.auth import create_access_token
from app.envelope import provision_user_dek
from app.models import ApiToken, generate_api_token


def _make_user(db, username="alice", role="user"):
    user = crud.create_user(db, username, "hash")
    provision_user_dek(db, user)
    if role != "user":
        user.role = role
        db.commit()
    return user


def _jwt_headers(user):
    token = create_access_token(
        {
            "sub": str(user.id),
            "username": user.username,
            "pwd_ver": user.password_version or 0,
        }
    )
    return {"Authorization": f"Bearer {token}"}


def _api_token(db, user):
    value = generate_api_token()
    db.add(ApiToken(user_id=user.id, name="test", token=value))
    db.commit()
    return value


class TestDualAuth:
    def test_jwt_reads_data(self, api_env):
        client, db = api_env
        user = _make_user(db)
        r = client.get("/api/v1/daily", headers=_jwt_headers(user))
        assert r.status_code == 200

    def test_api_token_reads_data_and_records_usage(self, api_env):
        client, db = api_env
        user = _make_user(db)
        token = _api_token(db, user)
        r = client.get("/api/v1/daily", headers={"X-API-Token": token})
        assert r.status_code == 200
        db.expire_all()
        assert db.query(ApiToken).filter(ApiToken.token == token).first().last_used_at is not None

    def test_api_token_writes_data_encrypted(self, api_env):
        client, db = api_env
        user = _make_user(db)
        token = _api_token(db, user)
        r = client.post(
            "/api/v1/daily",
            json={"date": "2026-11-17", "content": "token 写入"},
            headers={"X-API-Token": token},
        )
        assert r.status_code == 201
        db.expire_all()
        row = crud.get_daily_report(db, user.id, date(2026, 11, 17))
        assert row.content == ""  # encrypted at rest
        assert row.content_encrypted is not None

    def test_api_token_cannot_reach_admin_config(self, api_env):
        client, db = api_env
        user = _make_user(db, role="admin")
        token = _api_token(db, user)
        r = client.get("/api/v1/config", headers={"X-API-Token": token})
        assert r.status_code == 401  # 401 = wrong credential type, 403 is reserved for wrong role

    def test_api_token_cannot_reach_user_management(self, api_env):
        client, db = api_env
        user = _make_user(db, role="admin")
        token = _api_token(db, user)
        r = client.get("/api/v1/users", headers={"X-API-Token": token})
        assert r.status_code == 401

    def test_api_token_cannot_manage_tokens(self, api_env):
        client, db = api_env
        user = _make_user(db)
        token = _api_token(db, user)
        r = client.get("/api/v1/tokens", headers={"X-API-Token": token})
        assert r.status_code == 401

    def test_no_credentials_is_401(self, api_env):
        client, _ = api_env
        assert client.get("/api/v1/daily").status_code == 401

    def test_invalid_api_token_is_401(self, api_env):
        client, _ = api_env
        r = client.get("/api/v1/daily", headers={"X-API-Token": "deadbeef"})
        assert r.status_code == 401

    def test_invalid_jwt_is_401(self, api_env):
        client, _ = api_env
        r = client.get("/api/v1/daily", headers={"Authorization": "Bearer not-a-jwt"})
        assert r.status_code == 401

    def test_jwt_wins_when_both_supplied(self, api_env):
        client, db = api_env
        owner = _make_user(db, username="owner")
        other = _make_user(db, username="other")
        other_token = _api_token(db, other)

        client.post(
            "/api/v1/daily",
            json={"date": "2026-11-17", "content": "owner data"},
            headers=_jwt_headers(owner),
        )
        headers = {**_jwt_headers(owner), "X-API-Token": other_token}
        r = client.get("/api/v1/daily", headers=headers)
        assert r.status_code == 200
        assert [x["content"] for x in r.json()["reports"]] == ["owner data"]


class TestTokenUsageThrottle:
    def test_last_used_at_not_rewritten_within_interval(self, api_env):
        client, db = api_env
        user = _make_user(db)
        token = _api_token(db, user)
        headers = {"X-API-Token": token}

        client.get("/api/v1/daily", headers=headers)
        db.expire_all()
        first = db.query(ApiToken).filter(ApiToken.token == token).first().last_used_at
        assert first is not None

        client.get("/api/v1/daily", headers=headers)
        db.expire_all()
        second = db.query(ApiToken).filter(ApiToken.token == token).first().last_used_at
        assert second == first  # within the interval → no extra write

    def test_last_used_at_rewritten_when_stale(self, api_env):
        client, db = api_env
        user = _make_user(db)
        token = _api_token(db, user)
        row = db.query(ApiToken).filter(ApiToken.token == token).first()
        row.last_used_at = datetime.now(UTC) - timedelta(hours=2)
        db.commit()

        client.get("/api/v1/daily", headers={"X-API-Token": token})
        db.expire_all()
        updated = db.query(ApiToken).filter(ApiToken.token == token).first().last_used_at
        # SQLite returns naive UTC datetimes.
        naive_now = datetime.now(UTC).replace(tzinfo=None)
        assert updated is not None
        assert (naive_now - updated).total_seconds() < 60


class TestRoleForbidden:
    def test_non_admin_jwt_gets_403_on_admin_routes(self, api_env):
        client, db = api_env
        user = _make_user(db, role="user")

        r = client.get("/api/v1/users", headers=_jwt_headers(user))

        assert r.status_code == 403
