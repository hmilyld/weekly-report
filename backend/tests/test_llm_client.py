"""LLM client: request shaping and every failure branch, with no real network."""

import httpx
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.llm_client as llm
from app.models import AppConfig, Base


def completion(text: str) -> dict:
    return {"choices": [{"message": {"content": text}}]}


class FakeResponse:
    def __init__(self, payload=None, status_code=200):
        self._payload = payload
        self.status_code = status_code
        self.text = ""

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            request = httpx.Request("POST", "http://localhost/v1/chat/completions")
            response = httpx.Response(self.status_code, request=request, text=self.text)
            raise httpx.HTTPStatusError("failed", request=request, response=response)


class FakeClient:
    """Stands in for httpx.Client: records the call, replays a canned result."""

    response = None
    last = None

    def __init__(self, *args, **kwargs):
        self.timeout = kwargs.get("timeout")

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False

    def post(self, url, json=None, headers=None):
        FakeClient.last = {"url": url, "json": json, "headers": headers}
        if isinstance(FakeClient.response, Exception):
            raise FakeClient.response
        return FakeClient.response


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    session.add(
        AppConfig(
            id=1,
            llm_api_url="http://localhost:11434/v1/chat/completions",
            llm_model_name="llama2",
            api_key="",
        )
    )
    session.commit()
    yield session
    session.close()


@pytest.fixture()
def fake(monkeypatch):
    FakeClient.last = None
    FakeClient.response = FakeResponse(completion("生成结果"))
    monkeypatch.setattr(httpx, "Client", FakeClient)
    return FakeClient


ENTRIES = [("2026-11-16", "修复导出\n补充测试"), ("2026-11-17", "评审 PR")]


class TestChatCompletion:
    def test_weekly_shapes_the_request_and_returns_content(self, db, fake):
        result = llm.generate_weekly_report(db, ENTRIES)

        assert result == "生成结果"
        payload = fake.last["json"]
        assert payload["model"] == "llama2"
        assert payload["temperature"] == 0.7
        assert payload["messages"][0] == {"role": "system", "content": llm.SYSTEM_PROMPT}
        user_prompt = payload["messages"][1]["content"]
        assert user_prompt.startswith("本周日报记录：")
        assert "2026-11-16：修复导出；补充测试" in user_prompt

    def test_monthly_uses_its_own_system_prompt(self, db, fake):
        llm.generate_monthly_report(db, ENTRIES)

        assert fake.last["json"]["messages"][0]["content"] == llm.MONTHLY_SYSTEM_PROMPT
        assert fake.last["json"]["messages"][1]["content"].startswith("本月日报记录：")

    def test_api_key_becomes_a_bearer_header(self, db, fake):
        db.get(AppConfig, 1).api_key = "secret-key"
        db.commit()

        llm.generate_weekly_report(db, ENTRIES)
        assert fake.last["headers"]["Authorization"] == "Bearer secret-key"

    def test_no_authorization_header_without_a_key(self, db, fake):
        llm.generate_weekly_report(db, ENTRIES)
        assert "Authorization" not in fake.last["headers"]

    def test_timeout_is_reported_as_retryable(self, db, fake):
        fake.response = httpx.TimeoutException("slow")

        with pytest.raises(RuntimeError, match="timed out"):
            llm.generate_weekly_report(db, ENTRIES)

    def test_http_error_includes_the_status_code(self, db, fake):
        fake.response = FakeResponse(status_code=500)

        with pytest.raises(RuntimeError, match="500"):
            llm.generate_weekly_report(db, ENTRIES)

    def test_malformed_payload_is_reported(self, db, fake):
        fake.response = FakeResponse(payload={"choices": []})

        with pytest.raises(RuntimeError, match="Unexpected response"):
            llm.generate_weekly_report(db, ENTRIES)

    def test_connection_error_is_reported(self, db, fake):
        fake.response = httpx.ConnectError("refused")

        with pytest.raises(RuntimeError, match="Failed to connect"):
            llm.generate_weekly_report(db, ENTRIES)

    def test_invalid_configuration_is_rejected_before_the_call(self, db, fake):
        db.get(AppConfig, 1).llm_api_url = "ftp://example.com/completions"
        db.commit()

        with pytest.raises(RuntimeError, match="Invalid LLM configuration"):
            llm.generate_weekly_report(db, ENTRIES)
        assert fake.last is None


class TestBuildPrompt:
    def test_flattens_multiline_entries_into_one_line(self):
        prompt = llm._build_prompt("标题：", [("2026-11-16", "第一行\n第二行")])
        assert prompt == "标题：\n2026-11-16：第一行；第二行"


class TestConnectionCheck:
    def test_success_returns_the_model_reply(self, fake):
        fake.response = FakeResponse(completion("OK"))

        result = llm.test_connection("http://localhost:11434/v1/chat/completions", "llama2")

        assert result == {
            "success": True,
            "message": "Connection successful",
            "response": "OK",
        }

    def test_invalid_url_is_rejected_without_a_request(self, fake):
        result = llm.test_connection("file:///etc/passwd", "llama2")

        assert result["success"] is False
        assert "scheme" in result["message"]
        assert fake.last is None

    def test_timeout_is_reported(self, fake):
        fake.response = httpx.TimeoutException("slow")

        result = llm.test_connection("http://localhost:11434/v1/chat/completions", "llama2")

        assert result["success"] is False
        assert "timed out" in result["message"]

    def test_http_error_is_reported(self, fake):
        fake.response = FakeResponse(status_code=401)

        result = llm.test_connection("http://localhost:11434/v1/chat/completions", "llama2")

        assert result["success"] is False
        assert "401" in result["message"]

    def test_unexpected_failure_is_reported(self, fake):
        fake.response = httpx.ConnectError("refused")

        result = llm.test_connection("http://localhost:11434/v1/chat/completions", "llama2")

        assert result["success"] is False
        assert "Connection failed" in result["message"]
