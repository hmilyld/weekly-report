"""LLM client: call OpenAI-compatible Chat Completion API."""

import logging
from urllib.parse import urlparse

import httpx
from sqlalchemy.orm import Session

from . import crud

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "你是一个周报助手。请根据用户本周每天的工作记录（日报），生成一份简洁的周报。\n"
    "周报格式要求：\n"
    "### 本周工作\n"
    "将本周所有工作内容进行归类总结，按项目或模块聚合，不要逐天罗列。用有序列表呈现，每条前面用1. 2. 3. 编号。\n"
    "### 下周计划\n"
    "根据本周工作进展，合理推测或建议下周的重点任务。写 2~4 条即可，同样用有序列表编号。\n"
    "注意：语言简洁、专业，避免评价性词语（如优秀）。只输出周报内容，不要额外解释。"
)

TIMEOUT_SECONDS = 30

# SSRF protection: only allow http/https schemes
_ALLOWED_SCHEMES = {"http", "https"}
# Block private/internal IP ranges
_BLOCKED_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0", "[::1]", "metadata.google.internal"}
_BLOCKED_PREFIXES = (
    "10.",
    "172.16.",
    "172.17.",
    "172.18.",
    "172.19.",
    "172.2",
    "172.30.",
    "172.31.",
    "192.168.",
    "169.254.",
)


def _validate_llm_url(url: str) -> None:
    """Validate LLM URL to prevent SSRF attacks."""
    try:
        parsed = urlparse(url)
    except Exception as exc:
        raise ValueError("Invalid LLM API URL") from exc

    if parsed.scheme not in _ALLOWED_SCHEMES:
        raise ValueError(f"URL scheme '{parsed.scheme}' not allowed. Use http or https.")

    hostname = parsed.hostname or ""
    if hostname in _BLOCKED_HOSTS:
        raise ValueError(f"Access to '{hostname}' is not allowed.")

    for prefix in _BLOCKED_PREFIXES:
        if hostname.startswith(prefix):
            raise ValueError("Access to private IP ranges is not allowed.")


def build_user_prompt(daily_entries: list[tuple[str, str]]) -> str:
    """Build the user-side prompt from a list of (date_str, content) tuples."""
    lines = ["本周日报记录："]
    for date_str, content in daily_entries:
        clean = content.replace("\n", "；")
        lines.append(f"{date_str}：{clean}")
    return "\n".join(lines)


def generate_weekly_report(
    db: Session,
    daily_entries: list[tuple[str, str]],
) -> str:
    """
    Call the configured LLM to generate a weekly report.
    Returns the generated text.
    Raises RuntimeError on failure.
    """
    config = crud.get_app_config(db)
    api_url = config.llm_api_url
    model_name = config.llm_model_name
    api_key = config.api_key or ""

    # Validate URL before making request
    try:
        _validate_llm_url(api_url)
    except ValueError as e:
        raise RuntimeError(f"Invalid LLM configuration: {e}") from e

    user_prompt = build_user_prompt(daily_entries)

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    payload = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.7,
    }

    try:
        with httpx.Client(timeout=TIMEOUT_SECONDS) as client:
            response = client.post(api_url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
    except httpx.TimeoutException as err:
        raise RuntimeError("LLM request timed out. Please try again.") from err
    except httpx.HTTPStatusError as e:
        logger.error("LLM API error: %s %s", e.response.status_code, e.response.text[:500])
        raise RuntimeError(
            f"LLM API returned status {e.response.status_code}. Please check your configuration."
        ) from e
    except (KeyError, IndexError) as e:
        logger.error("Unexpected LLM response: %s", e)
        raise RuntimeError("Unexpected response from LLM. Please check model configuration.") from e
    except RuntimeError:
        raise
    except Exception as e:
        logger.error("LLM call failed: %s", e)
        raise RuntimeError("Failed to connect to LLM. Please check your API URL and key.") from e


def test_connection(api_url: str, model_name: str, api_key: str = "") -> dict:
    """
    Send a simple test message to verify the LLM endpoint works.
    Returns {"success": bool, "message": str, "response": str|None}.
    """
    # Validate URL before making request
    try:
        _validate_llm_url(api_url)
    except ValueError as e:
        return {"success": False, "message": str(e), "response": None}

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    payload = {
        "model": model_name,
        "messages": [
            {"role": "user", "content": "Hello, respond with just 'OK'."},
        ],
        "temperature": 0.1,
        "max_tokens": 10,
    }

    try:
        with httpx.Client(timeout=15) as client:
            response = client.post(api_url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            reply = data["choices"][0]["message"]["content"].strip()
            return {
                "success": True,
                "message": "Connection successful",
                "response": reply,
            }
    except httpx.TimeoutException:
        return {"success": False, "message": "Request timed out (15s)", "response": None}
    except httpx.HTTPStatusError as e:
        return {
            "success": False,
            "message": f"HTTP {e.response.status_code}. Please check your configuration.",
            "response": None,
        }
    except Exception as e:
        logger.error("LLM test failed: %s", e)
        return {
            "success": False,
            "message": "Connection failed. Check URL and credentials.",
            "response": None,
        }
