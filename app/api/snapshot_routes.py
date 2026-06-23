import json
from pathlib import Path
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, status
from fastapi.responses import FileResponse
from app.services.snapshot_service import snapshot_service

router = APIRouter(prefix="/api/snapshots", tags=["Snapshots"])

@router.post("", status_code=status.HTTP_201_CREATED, summary="Save a new violation snapshot")
async def create_snapshot(
    camera_id: str = Form(..., description="ID of the originating camera"),
    metadata_json: str = Form("{}", description="Stringified JSON object containing telemetry/violation data"),
    file: UploadFile = File(..., description="The raw encoded image frame (JPEG/PNG)")
):
    """
    Accepts an uploaded image file along with contextual metadata and persists them
    into the daily partitioned artifact storage system.
    """
    try:
        metadata_dict = json.loads(metadata_json)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid metadata_json string.")

    frame_bytes = await file.read()
    rel_path = snapshot_service.save_snapshot(camera_id, frame_bytes, metadata_dict)
    
    return {
        "status": "success", 
        "message": "Snapshot persisted successfully",
        "path": rel_path
    }

@router.get("/{year}/{month}/{day}/{filename}", summary="Retrieve snapshot image")
def get_snapshot_image(year: str, month: str, day: str, filename: str):
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
def get_snapshot_metadata(year: str, month: str, day: str, filename: str):
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
