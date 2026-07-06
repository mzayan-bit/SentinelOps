"""
SentinelOps — Model Registry API Routes
=========================================
"""

import logging
from typing import List

from fastapi import APIRouter, HTTPException, status, Depends
from app.core.security import Role, get_current_user, require_role
from app.db.models import UserModel

from app.services.model_registry import model_registry_service
from schemas.model_registry import RegisteredModel, ModelSwitchRequest

logger = logging.getLogger("sentinelops.api.models")

router = APIRouter(prefix="/api/models", tags=["Models"])


@router.get("", response_model=List[RegisteredModel])
async def list_models(user: UserModel = Depends(require_role(Role.VIEWER))):
    """Retrieve a list of all registered YOLO models."""
    return model_registry_service.list_models()


@router.get("/active", response_model=RegisteredModel)
async def get_active_model(user: UserModel = Depends(require_role(Role.VIEWER))):
    """Get the currently active YOLO model."""
    model = model_registry_service.get_active_model()
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active model found in the registry."
        )
    return model


@router.post("", response_model=RegisteredModel, status_code=status.HTTP_201_CREATED)
async def register_model(model: RegisteredModel, user: UserModel = Depends(require_role(Role.ORG_ADMIN))):
    """Register a new YOLO model or update an existing one."""
    return model_registry_service.register_model(model)


@router.post("/active", response_model=RegisteredModel)
async def switch_active_model(request: ModelSwitchRequest, user: UserModel = Depends(require_role(Role.SUPERVISOR))):
    """Switch the active YOLO model dynamically at runtime."""
    try:
        active_model = model_registry_service.set_active_model(request.name, request.version)
        if not active_model:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Model '{request.name}' (v{request.version}) not found in the registry."
            )
        return active_model
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error switching model: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to switch model in the inference engine."
        )
