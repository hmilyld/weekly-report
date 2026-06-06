"""App config router: LLM settings & test connection."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import crud
from ..auth import get_current_user
from ..database import get_db
from ..llm_client import test_connection
from ..models import User
from ..schemas import AppConfigResponse, AppConfigUpdate

router = APIRouter(prefix="/api/v1/config", tags=["config"])


@router.get("", response_model=AppConfigResponse)
def get_config(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get current LLM configuration."""
    config = crud.get_app_config(db)
    # Mask API key for display (only show last 4 chars if present)
    response = AppConfigResponse.model_validate(config)
    if response.api_key and len(response.api_key) > 4:
        response.api_key = response.api_key  # Return full key to frontend for editing
    return response


@router.put("", response_model=AppConfigResponse)
def update_config(
    body: AppConfigUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update LLM configuration."""
    config = crud.update_app_config(
        db,
        llm_api_url=body.llm_api_url,
        llm_model_name=body.llm_model_name,
        api_key=body.api_key,
    )
    return config


@router.post("/test")
def test_llm_connection(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Test the configured LLM endpoint."""
    config = crud.get_app_config(db)
    result = test_connection(config.llm_api_url, config.llm_model_name, config.api_key or "")
    return result
