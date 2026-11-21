"""Invalid input answers 4xx (never 500) and the SPA never serves outside dist."""

import main
from app import crud
from app.auth import create_access_token, hash_password
from app.envelope import provision_user_dek


def _admin(client, db):
    user = crud.create_user(db, "admin", hash_password("Passw0rd1"), role="admin")
    provision_user_dek(db, user)
    token = create_access_token(
        {"sub": str(user.id), "username": user.username, "pwd_ver": user.password_version or 0}
    )
    return {"Authorization": f"Bearer {token}"}


class TestReportPathParams:
    def test_month_out_of_range_is_422(self, api_env):
        client, db = api_env
        headers = _admin(client, db)

        assert client.post("/api/v1/monthly/2026/13", headers=headers).status_code == 422
        assert client.post("/api/v1/monthly/2026/0", headers=headers).status_code == 422
        assert client.get("/api/v1/monthly/2026/13", headers=headers).status_code == 422

    def test_week_start_overflow_is_400(self, api_env):
        client, db = api_env
        headers = _admin(client, db)

        response = client.post("/api/v1/weekly/9999-12-31", headers=headers)

        assert response.status_code == 400
        assert "9998" in response.json()["detail"]

    def test_daily_week_overflow_is_400(self, api_env):
        client, db = api_env
        headers = _admin(client, db)

        response = client.get("/api/v1/daily/week/9999-12-31", headers=headers)

        assert response.status_code == 400


class TestStaticFileResolution:
    def _static_dir(self, tmp_path, monkeypatch):
        dist = tmp_path / "dist"
        (dist / "assets").mkdir(parents=True)
        (dist / "index.html").write_text("INDEX", encoding="utf-8")
        (dist / "app.js").write_text("APP", encoding="utf-8")
        sibling = tmp_path / "dist-old"
        sibling.mkdir()
        (sibling / "secret.txt").write_text("SECRET", encoding="utf-8")
        monkeypatch.setattr(main, "STATIC_DIR", dist)
        return dist

    def test_serves_files_inside_dist(self, tmp_path, monkeypatch):
        self._static_dir(tmp_path, monkeypatch)

        assert main.resolve_static_file("app.js").read_text(encoding="utf-8") == "APP"

    def test_blocks_sibling_directory_with_same_prefix(self, tmp_path, monkeypatch):
        """Regression: '../dist-old/x' must not pass a string prefix check."""
        self._static_dir(tmp_path, monkeypatch)

        assert main.resolve_static_file("../dist-old/secret.txt") is None

    def test_blocks_absolute_escape(self, tmp_path, monkeypatch):
        self._static_dir(tmp_path, monkeypatch)

        assert main.resolve_static_file("../../etc/passwd") is None

    def test_missing_file_returns_none(self, tmp_path, monkeypatch):
        self._static_dir(tmp_path, monkeypatch)

        assert main.resolve_static_file("nope.js") is None


class TestHealth:
    def test_health_pings_the_database(self, api_env, monkeypatch):
        called = []
        monkeypatch.setattr(main, "ping_database", lambda: called.append(True))
        client, _db = api_env

        response = client.get("/api/v1/health")

        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
        assert called == [True]
