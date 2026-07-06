import uuid
from typing import List, Dict
from fastapi import APIRouter, Depends, HTTPException, status
from app.core.security import Role, get_current_user, require_role
from app.services.camera_manager import CameraManager
from app.services.health_monitor import health_monitor, CameraHealth
from app.services.cache_service import cached, invalidate_prefix
from schemas.camera import CameraCreate, CameraResponse
from app.services.task_worker import task_worker

router = APIRouter(prefix="/api/cameras", tags=["Cameras"])

# Global singleton for the lifetime of the application
camera_manager = CameraManager()

@router.get("/debug/tasks", summary="List background tasks (Debug)")
async def debug_tasks():
    return {"tasks": task_worker.list_tasks()}

@router.get("", response_model=List[CameraResponse], summary="List all cameras")
@cached(prefix="cameras:", ttl_seconds=5)
async def list_cameras(user: UserModel = Depends(require_role(Role.VIEWER))):
    """Retrieves all registered cameras and their current statuses."""
    cameras = camera_manager.list_cameras()
    return [
        CameraResponse(
            id=c.id,
            source=c.source,
            name=c.name,
            status=c.status.value
        ) for c in cameras
    ]

@router.get("/health/all", response_model=Dict[str, CameraHealth], summary="Get health of all cameras")
@cached(prefix="health:", ttl_seconds=5)
async def get_all_health(user: UserModel = Depends(require_role(Role.VIEWER))):
    """Returns the real-time telemetry and health data for all monitored streams."""
    return health_monitor.get_all_health()

@router.post("", response_model=CameraResponse, status_code=status.HTTP_201_CREATED, summary="Register a new camera")
async def add_camera(camera_in: CameraCreate, user: UserModel = Depends(require_role(Role.ORG_ADMIN))):
    """Registers a new video source and assigns it a UUID."""
    cam_id = camera_manager.add_camera(source=camera_in.source, name=camera_in.name)
    
    # Retrieve the created object to return it
    cameras = camera_manager.list_cameras()
    new_cam = next((c for c in cameras if c.id == cam_id), None)
    if not new_cam:
        raise HTTPException(status_code=500, detail="Failed to retrieve created camera.")
        
    await invalidate_prefix("cameras:")
    return CameraResponse(
        id=new_cam.id,
        source=new_cam.source,
        name=new_cam.name,
        status=new_cam.status.value
    )

@router.get("/{camera_id}/health", response_model=CameraHealth, summary="Get camera health metrics")
@cached(prefix="health:", ttl_seconds=5)
async def get_camera_health(camera_id: str, user: UserModel = Depends(require_role(Role.VIEWER))):
    """Retrieves latency, FPS, and status for a specific camera."""
    health = health_monitor.get_health(camera_id)
    if not health:
        raise HTTPException(status_code=404, detail="Health data not found for this camera.")
    return health

@router.delete("/{camera_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Remove a camera")
async def remove_camera(camera_id: uuid.UUID, user: UserModel = Depends(require_role(Role.ORG_ADMIN))):
    """Stops and removes the specified camera from the manager."""
    success = camera_manager.remove_camera(camera_id)
    if not success:
        raise HTTPException(status_code=404, detail="Camera not found.")
    await invalidate_prefix("cameras:")
    await invalidate_prefix("health:")

@router.post("/{camera_id}/start", summary="Start camera processing")
async def start_camera(camera_id: uuid.UUID, user: UserModel = Depends(require_role(Role.SUPERVISOR))):
    """Starts the video processing pipeline for the given camera."""
    try:
        camera_manager.start_camera(camera_id)
        # Initialize tracking as offline initially till frames flow
        health_monitor.record_offline(str(camera_id))
        await invalidate_prefix("cameras:")
        await invalidate_prefix("health:")
        return {"status": "success", "message": f"Camera {camera_id} started."}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/{camera_id}/stop", summary="Stop camera processing")
async def stop_camera(camera_id: uuid.UUID, user: UserModel = Depends(require_role(Role.SUPERVISOR))):
    """Stops the video processing pipeline for the given camera."""
    try:
        camera_manager.stop_camera(camera_id)
        health_monitor.record_offline(str(camera_id))
        await invalidate_prefix("cameras:")
        await invalidate_prefix("health:")
        return {"status": "success", "message": f"Camera {camera_id} stopped."}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
