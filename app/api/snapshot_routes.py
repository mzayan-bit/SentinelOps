import json
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from fastapi.responses import FileResponse
from app.core.security import Role, get_current_user, require_role
from app.services.snapshot_service import snapshot_service
from app.services.task_worker import task_worker

router = APIRouter(prefix="/api/snapshots", tags=["Snapshots"])

@router.post("", status_code=status.HTTP_202_ACCEPTED, summary="Save a new violation snapshot")
async def create_snapshot(
    camera_id: str = Form(..., description="ID of the originating camera"),
    metadata_json: str = Form("{}", description="Stringified JSON object containing telemetry/violation data"),
    file: UploadFile = File(..., description="The raw encoded image frame (JPEG/PNG)"),
    user: User = Depends(require_role(Role.SUPERVISOR))
):
    """
    Accepts an uploaded image file along with contextual metadata and submits
    the persistence operation to the background task worker.
    """
    try:
        metadata_dict = json.loads(metadata_json)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid metadata_json string.")

    # Read bytes synchronously before handing off (UploadFile is request-bound)
    frame_bytes = await file.read()

    task_id = task_worker.submit(
        snapshot_service.save_snapshot,
        camera_id,
        frame_bytes,
        metadata_dict,
        task_type="snapshot_save",
    )

    return {
        "status": "accepted",
        "task_id": task_id,
        "message": "Snapshot save submitted to background worker.",
    }

@router.get("/{year}/{month}/{day}/{filename}", summary="Retrieve snapshot image")
def get_snapshot_image(year: str, month: str, day: str, filename: str, user: User = Depends(require_role(Role.VIEWER))):
    """
    Streams the raw snapshot image directly back to the client for rendering in the dashboard.
    """
    rel_path = f"{year}/{month}/{day}/{filename}"
    
    try:
        full_path = snapshot_service.get_snapshot_path(rel_path)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
        
    if not full_path.exists() or not full_path.is_file():
        raise HTTPException(status_code=404, detail="Snapshot image not found on disk.")
        
    # Determine basic media type
    media_type = "image/png" if filename.lower().endswith(".png") else "image/jpeg"
    return FileResponse(str(full_path), media_type=media_type)

@router.get("/{year}/{month}/{day}/{filename}/metadata", summary="Retrieve snapshot metadata")
def get_snapshot_metadata(year: str, month: str, day: str, filename: str, user: User = Depends(require_role(Role.VIEWER))):
    """
    Retrieves the contextual JSON metadata sidecar file saved alongside a specific snapshot image.
    """
    # Replace the media extension with .json to target the sidecar file
    meta_filename = Path(filename).with_suffix(".json").name
    rel_path = f"{year}/{month}/{day}/{meta_filename}"
    
    try:
        full_path = snapshot_service.get_snapshot_path(rel_path)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
        
    if not full_path.exists() or not full_path.is_file():
        raise HTTPException(status_code=404, detail="Snapshot metadata not found on disk.")
    
    with open(full_path, "r") as f:
        data = json.load(f)
        
    return data
