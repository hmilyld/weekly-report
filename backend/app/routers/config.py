"""App config router: LLM settings & test connection."""

import re

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import crud
from ..auth import require_admin
from ..database import get_db
from ..llm_client import test_connection
from ..models import AppConfig, User
from ..schemas import AppConfigResponse, AppConfigUpdate, LlmTestResponse

router = APIRouter(prefix="/api/v1/config", tags=["config"])

MASK_CHAR = "*"
# Masks always contain a run of at least 6 asterisks; real API keys do not.
_MASKED_PATTERN = re.compile(r"\*{4,}")


def _mask_api_key(key: str | None) -> str | None:
    """Mask the API key for every response (GET and PUT alike).

    Never returns a usable secret, including for short keys. The masked value
    always contains ``*`` so the client can tell "unchanged" from a real key.
    """
    if not key:
        return key
    if len(key) <= 12:
        return MASK_CHAR * 8
    return key[:3] + MASK_CHAR * (len(key) - 7) + key[-4:]


def _to_response(config: AppConfig) -> AppConfigResponse:
    response = AppConfigResponse.model_validate(config)
    response.api_key = _mask_api_key(response.api_key)
    return response


def _reject_masked_secret(api_key: str | None) -> str | None:
    """A masked value means "leave the stored key alone"; absent also means unchanged."""
    if api_key is not None and _MASKED_PATTERN.search(api_key):
        return None
    return api_key


@router.get("", response_model=AppConfigResponse)
def get_config(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Get current LLM configuration (admin only)."""
    return _to_response(crud.get_app_config(db))


@router.put("", response_model=AppConfigResponse)
def update_config(
    body: AppConfigUpdate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Update LLM configuration (admin only). Responds with the masked key."""
    config = crud.update_app_config(
        db,
        llm_api_url=body.llm_api_url,
        llm_model_name=body.llm_model_name,
        api_key=_reject_masked_secret(body.api_key),
    )
    return _to_response(config)


@router.post("/test", response_model=LlmTestResponse)
def test_llm_connection(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Test the configured LLM endpoint (admin only)."""
    config = crud.get_app_config(db)
    result = test_connection(config.llm_api_url, config.llm_model_name, config.api_key or "")
    return result
