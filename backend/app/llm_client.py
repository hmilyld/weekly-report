"""LLM client: call OpenAI-compatible Chat Completion API."""

import httpx
from sqlalchemy.orm import Session

from . import crud

SYSTEM_PROMPT = (
    "你是一个周报助手。请根据用户本周每天的工作记录（日报），生成一份简洁的周报。\n"
    "周报格式要求：\n"
    "- 第一部分：【本周工作汇总】\n"
    "  将本周所有工作内容进行归类总结，按项目或模块聚合，不要逐天罗列。用条列式呈现，每条前面用“-”开头。\n"
    "- 第二部分：【下周计划】\n"
    "  根据本周工作进展，合理推测或建议下周的重点任务。写 2~4 条即可。\n"
    "注意：语言简洁、专业，避免评价性词语（如“优秀”）。只输出周报内容，不要额外解释。"
)

TIMEOUT_SECONDS = 30


def build_user_prompt(daily_entries: list[tuple[str, str]]) -> str:
    """
    Build the user-side prompt from a list of (date_str, content) tuples.
    Replaces newlines in content with semicolons.
    """
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
        raise RuntimeError("LLM request timed out (30s)") from err
    except httpx.HTTPStatusError as e:
        raise RuntimeError(
            f"LLM API error: {e.response.status_code} - {e.response.text[:200]}"
        ) from e
    except (KeyError, IndexError) as e:
        raise RuntimeError(f"Unexpected LLM response format: {e}") from e
    except Exception as e:
        raise RuntimeError(f"LLM call failed: {e!s}") from e


def test_connection(api_url: str, model_name: str, api_key: str = "") -> dict:
    """
    Send a simple test message to verify the LLM endpoint works.
    Returns {"success": bool, "message": str, "response": str|None}.
    """
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
        return {
            "success": False,
            "message": "Request timed out (15s)",
            "response": None,
        }
    except httpx.HTTPStatusError as e:
        return {
            "success": False,
            "message": f"HTTP {e.response.status_code}: {e.response.text[:200]}",
            "response": None,
        }
    except Exception as e:
        return {"success": False, "message": str(e), "response": None}
