"""
SentinelOps — Model Registry API Routes
=========================================
"""

import logging
from typing import List, Dict, Any

from fastapi import APIRouter, HTTPException, status, Depends
from app.core.security import Role, get_current_user, require_role
from app.db.models import UserModel

from app.services.model_registry import model_registry_service
from schemas.model_registry import (
    RegisteredModel, 
    ModelSwitchRequest, 
    ModelPromoteRequest, 
    DeploymentLog
)

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

@router.post("/promote", response_model=RegisteredModel)
async def promote_model(request: ModelPromoteRequest, user: UserModel = Depends(require_role(Role.ORG_ADMIN))):
    """
    Promote a model to a new environment (e.g. Development -> Staging).
    If promoted to PRODUCTION, triggers hot-loading.
    """
    try:
        return model_registry_service.promote_model(
            request.name, 
            request.version, 
            request.target_environment, 
            request.notes or ""
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.post("/rollback", response_model=RegisteredModel)
async def rollback_model(user: UserModel = Depends(require_role(Role.ORG_ADMIN))):
    """
    Instantly rolls back the PRODUCTION environment to the last known-good stable model.
    """
    try:
        return model_registry_service.rollback_model()
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.get("/deployments", response_model=List[DeploymentLog])
async def get_deployments(user: UserModel = Depends(require_role(Role.VIEWER))):
    """
    Retrieve the immutable deployment history ledger.
    """
    return model_registry_service.get_deployment_history()

@router.get("/compare", response_model=Dict[str, Any])
async def compare_models(name_a: str, version_a: str, name_b: str, version_b: str, user: UserModel = Depends(require_role(Role.VIEWER))):
    """
    Compare metrics and latency between two model versions.
    """
    try:
        return model_registry_service.compare_models(name_a, version_a, name_b, version_b)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

