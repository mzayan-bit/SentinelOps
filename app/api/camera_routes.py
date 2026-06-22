import uuid
from typing import List
from fastapi import APIRouter, HTTPException, status
from app.services.camera_manager import CameraManager
from schemas.camera import CameraCreate, CameraResponse

router = APIRouter(prefix="/api/cameras", tags=["Cameras"])

# Global singleton for the lifetime of the application
camera_manager = CameraManager()

@router.get("", response_model=List[CameraResponse], summary="List all cameras")
def list_cameras():
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

@router.post("", response_model=CameraResponse, status_code=status.HTTP_201_CREATED, summary="Register a new camera")
def add_camera(camera_in: CameraCreate):
    """Registers a new video source and assigns it a UUID."""
    cam_id = camera_manager.add_camera(source=camera_in.source, name=camera_in.name)
    
    # Retrieve the created object to return it
    cameras = camera_manager.list_cameras()
    new_cam = next((c for c in cameras if c.id == cam_id), None)
    if not new_cam:
        raise HTTPException(status_code=500, detail="Failed to retrieve created camera.")
        
    return CameraResponse(
        id=new_cam.id,
        source=new_cam.source,
        name=new_cam.name,
        status=new_cam.status.value
    )

@router.delete("/{camera_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Remove a camera")
def remove_camera(camera_id: uuid.UUID):
    """Stops and removes the specified camera from the manager."""
    success = camera_manager.remove_camera(camera_id)
    if not success:
        raise HTTPException(status_code=404, detail="Camera not found.")

@router.post("/{camera_id}/start", summary="Start camera processing")
def start_camera(camera_id: uuid.UUID):
    """Starts the video processing pipeline for the given camera."""
    try:
        camera_manager.start_camera(camera_id)
        return {"status": "success", "message": f"Camera {camera_id} started."}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/{camera_id}/stop", summary="Stop camera processing")
def stop_camera(camera_id: uuid.UUID):
    """Stops the video processing pipeline for the given camera."""
    try:
        camera_manager.stop_camera(camera_id)
        return {"status": "success", "message": f"Camera {camera_id} stopped."}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
