import os
import json
import uuid
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

class SnapshotService:
    """
    Manages physical storage of incident screenshots and associated metadata.
    Implements a robust YYYY/MM/DD partitioning structure to avoid directory limits.
    """
    def __init__(self, base_dir: str = "artifacts/screenshots"):
        self.base_dir = Path(base_dir)
        # Ensure the base artifacts directory exists at startup
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save_snapshot(self, camera_id: str, frame_bytes: bytes, metadata: Dict[str, Any]) -> str:
        """
        Persists a frame as a JPEG and saves its metadata footprint alongside it.
        
        Args:
            camera_id: The ID of the camera source.
            frame_bytes: Raw bytes of the encoded image (usually JPEG).
            metadata: Supplemental dictionary detailing the violation or context.
            
        Returns:
            str: The relative path to the saved image file (e.g., '2026/06/23/cam1_...jpg')
        """
        now = datetime.now()
        
        # Partition directory: artifacts/screenshots/YYYY/MM/DD
        date_path = self.base_dir / f"{now.year:04d}" / f"{now.month:02d}" / f"{now.day:02d}"
        date_path.mkdir(parents=True, exist_ok=True)

        # Unique naming avoiding race conditions across threads
        file_id = f"{camera_id}_{now.strftime('%H%M%S')}_{uuid.uuid4().hex[:8]}"
        img_path = date_path / f"{file_id}.jpg"
        meta_path = date_path / f"{file_id}.json"

        # 1. Persist Image
        with open(img_path, "wb") as f:
            f.write(frame_bytes)

        # 2. Persist Metadata JSON
        full_metadata = {
            "camera_id": camera_id,
            "timestamp": time.time(),
            "datetime": now.isoformat(),
            **metadata
        }
        with open(meta_path, "w") as f:
            json.dump(full_metadata, f, indent=2)

        # Return cleanly scoped relative path for API/frontend consumption
        return str(img_path.relative_to(self.base_dir))

    def get_snapshot_path(self, relative_path: str) -> Path:
        """Resolves a relative path request to the absolute filesystem location."""
        # Note: In a true prod env, path sanitization is needed to prevent directory traversal
        clean_path = Path(relative_path)
        if ".." in clean_path.parts:
            raise ValueError("Directory traversal attempt blocked.")
        return self.base_dir / clean_path

snapshot_service = SnapshotService()
