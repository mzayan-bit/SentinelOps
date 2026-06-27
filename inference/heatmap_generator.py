"""
SentinelOps — Occupancy Heatmap Generator
=========================================
Aggregates spatial coordinate data over the lifespan of a video feed
to generate density heatmaps (person movement & compliance violations).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Tuple

import cv2
import numpy as np

logger = logging.getLogger("sentinelops.heatmap")

class HeatmapGenerator:
    """Stateful aggregator for generating CV heatmaps from spatial points."""

    def __init__(self, width: int, height: int, background_frame: np.ndarray | None = None):
        """
        Parameters
        ----------
        width : int
            Video frame width.
        height : int
            Video frame height.
        background_frame : np.ndarray | None
            A reference BGR frame (e.g., the first frame of the video).
            If None, a black background will be used.
        """
        self.width = width
        self.height = height
        
        if background_frame is not None:
            self.background_frame = background_frame.copy()
        else:
            self.background_frame = np.zeros((height, width, 3), dtype=np.uint8)

        # 2D arrays to accumulate raw point counts
        self.movement_accumulator = np.zeros((height, width), dtype=np.float32)
        self.violation_accumulator = np.zeros((height, width), dtype=np.float32)

    def add_movement_point(self, x: float, y: float) -> None:
        """Record a standard movement point (e.g., bottom-center of bounding box)."""
        ix, iy = int(x), int(y)
        if 0 <= ix < self.width and 0 <= iy < self.height:
            self.movement_accumulator[iy, ix] += 1.0

    def add_violation_point(self, x: float, y: float) -> None:
        """Record a point where a compliance violation occurred."""
        ix, iy = int(x), int(y)
        if 0 <= ix < self.width and 0 <= iy < self.height:
            self.violation_accumulator[iy, ix] += 1.0

    def _generate_heatmap_overlay(self, accumulator: np.ndarray, colormap: int = cv2.COLORMAP_JET) -> np.ndarray:
        """Core logic to convert raw point densities into a colored, blurred overlay."""
        # 1. Apply a significant Gaussian Blur to expand the single pixels into smooth heat blobs
        # Using a kernel size relative to standard 1080p width
        kernel_size = max(11, int(self.width * 0.05)) 
        if kernel_size % 2 == 0:
            kernel_size += 1
            
        blurred = cv2.GaussianBlur(accumulator, (kernel_size, kernel_size), 0)

        # 2. Normalize to 0-255 uint8 range
        max_val = np.max(blurred)
        if max_val > 0:
            normalized = (blurred / max_val * 255).astype(np.uint8)
        else:
            normalized = np.zeros_like(blurred, dtype=np.uint8)

        # 3. Apply the OpenCV Colormap
        heatmap_colored = cv2.applyColorMap(normalized, colormap)

        # 4. We want transparent pixels where density is zero.
        # But cv2.addWeighted works globally. A better approach is to create a mask.
        mask = normalized > 10  # Only apply color where there is at least some heat
        
        overlay = self.background_frame.copy()
        
        if np.any(mask):
            # We blend the colored heatmap onto the background frame where mask is true
            alpha = 0.6  # Transparency of the heatmap
            
            # Extract the regions
            bg_region = overlay[mask]
            hm_region = heatmap_colored[mask]
            
            # Blend
            overlay[mask] = cv2.addWeighted(hm_region, alpha, bg_region, 1 - alpha, 0)
            
        return overlay

    def generate_movement_heatmap(self) -> np.ndarray:
        """Generate the occupancy movement heatmap using JET colormap."""
        return self._generate_heatmap_overlay(self.movement_accumulator, cv2.COLORMAP_JET)

    def generate_violation_hotspot(self) -> np.ndarray:
        """Generate the violation hotspot map using HOT colormap."""
        return self._generate_heatmap_overlay(self.violation_accumulator, cv2.COLORMAP_HOT)

    def save_heatmaps(self, output_dir: str | Path, prefix: str = "") -> None:
        """Generate and save both heatmaps to the specified directory."""
        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)
        
        movement_img = self.generate_movement_heatmap()
        violation_img = self.generate_violation_hotspot()
        
        m_filename = f"{prefix}_movement_heatmap.jpg" if prefix else "movement_heatmap.jpg"
        v_filename = f"{prefix}_violation_hotspot.jpg" if prefix else "violation_hotspot.jpg"
        
        m_path = out_path / m_filename
        v_path = out_path / v_filename
        
        cv2.imwrite(str(m_path), movement_img)
        cv2.imwrite(str(v_path), violation_img)
        
        logger.info(f"Saved movement heatmap to: {m_path}")
        logger.info(f"Saved violation hotspot to: {v_path}")
