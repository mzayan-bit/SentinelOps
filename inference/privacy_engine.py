"""
SentinelOps — Privacy Engine
============================
Lightweight module for applying privacy-preserving face blurring.
Uses OpenCV's Haar Cascades for fast CPU-bound detection.
"""

from __future__ import annotations

import logging
from pathlib import Path
import cv2
import numpy as np

logger = logging.getLogger("sentinelops.privacy")

class PrivacyEngine:
    """Detects and blurs faces in an image/frame to preserve privacy."""

    def __init__(self, cascade_path: str = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'):
        """
        Initialize the Haar Cascade for face detection.
        """
        cascade_file = Path(cascade_path)
        if not cascade_file.exists():
            logger.warning(f"Haar cascade not found at {cascade_path}. Falling back to default distribution.")
            cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            
        try:
            self.face_cascade = getattr(cv2, 'CascadeClassifier')(cascade_path)
            if self.face_cascade.empty():
                logger.error("Failed to load Haar cascade classifier. Privacy mode will be disabled.")
                self._is_ready = False
            else:
                self._is_ready = True
        except AttributeError:
            logger.error("OpenCV was built without CascadeClassifier support. Privacy mode disabled.")
            self._is_ready = False

    def apply_privacy(self, frame: np.ndarray) -> np.ndarray:
        """
        Detect faces and apply a Gaussian blur over the regions of interest (ROI).
        
        Parameters
        ----------
        frame : np.ndarray
            The BGR frame to process.
            
        Returns
        -------
        np.ndarray
            The processed frame with blurred faces.
        """
        if not self._is_ready or frame is None or frame.size == 0:
            return frame

        # Convert to grayscale for Haar cascade
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Detect faces
        # scaleFactor=1.1, minNeighbors=5, minSize=(30, 30) are standard fast parameters
        faces = self.face_cascade.detectMultiScale(
            gray, 
            scaleFactor=1.1, 
            minNeighbors=5, 
            minSize=(30, 30)
        )

        annotated_frame = frame.copy()

        for (x, y, w, h) in faces:
            # Extract Region of Interest
            roi = annotated_frame[y:y+h, x:x+w]
            
            # Apply a heavy blur. Kernel size depends on box size to ensure deep anonymization
            k_size = (w // 2) | 1  # ensure odd number
            if k_size < 3:
                k_size = 3
                
            blurred_roi = cv2.GaussianBlur(roi, (k_size, k_size), 30)
            
            # Replace ROI in original frame
            annotated_frame[y:y+h, x:x+w] = blurred_roi

        return annotated_frame
