"""App config router: LLM settings & test connection."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import crud
from ..auth import require_admin
from ..database import get_db
from ..llm_client import test_connection
from ..models import User
from ..schemas import AppConfigResponse, AppConfigUpdate

router = APIRouter(prefix="/api/v1/config", tags=["config"])


def _mask_api_key(key: str | None) -> str | None:
    """Mask API key, showing only first 3 and last 4 characters."""
    if not key or len(key) <= 8:
        return key
    return key[:3] + "*" * (len(key) - 7) + key[-4:]


@router.get("", response_model=AppConfigResponse)
def get_config(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Get current LLM configuration (admin only)."""
    config = crud.get_app_config(db)
    response = AppConfigResponse.model_validate(config)
    response.api_key = _mask_api_key(response.api_key)
    return response


@router.put("", response_model=AppConfigResponse)
def update_config(
    body: AppConfigUpdate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Update LLM configuration (admin only)."""
    config = crud.update_app_config(
        db,
        llm_api_url=body.llm_api_url,
        llm_model_name=body.llm_model_name,
        api_key=body.api_key,
    )
    return config


@router.post("/test")
def test_llm_connection(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Test the configured LLM endpoint (admin only)."""
    config = crud.get_app_config(db)
    result = test_connection(config.llm_api_url, config.llm_model_name, config.api_key or "")
    return result
