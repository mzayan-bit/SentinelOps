"""
SentinelOps — Confidence Threshold Service
============================================
"""

import json
import logging
from typing import Optional

from config.settings import settings
from schemas.thresholds import ThresholdConfig

logger = logging.getLogger("sentinelops.thresholds")

class ThresholdService:
    def __init__(self):
        self.config_file = settings.registry_dir / "thresholds.json"
        # Seed default config if missing
        if not self.config_file.parent.exists():
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
        if not self.config_file.exists():
            self._save(ThresholdConfig(global_threshold=settings.confidence_threshold))

    def _load(self) -> ThresholdConfig:
        try:
            with open(self.config_file, "r") as f:
                data = json.load(f)
                return ThresholdConfig(**data)
        except (json.JSONDecodeError, FileNotFoundError) as e:
            logger.warning(f"Failed to load thresholds, falling back to default: {e}")
            return ThresholdConfig(global_threshold=settings.confidence_threshold)

    def _save(self, config: ThresholdConfig):
        with open(self.config_file, "w") as f:
            json.dump(config.model_dump(), f, indent=4)

    def get_config(self) -> ThresholdConfig:
        return self._load()

    def update_config(self, config: ThresholdConfig) -> ThresholdConfig:
        self._save(config)
        return config

    def get_threshold(self, class_name: str) -> float:
        """Get the specific threshold for a class, or fallback to the global threshold."""
        config = self._load()
        return config.per_class.get(class_name, config.global_threshold)

    def get_min_threshold(self) -> float:
        """Get the absolute minimum threshold to optimize YOLO inference."""
        config = self._load()
        if not config.per_class:
            return config.global_threshold
        return min(config.global_threshold, min(config.per_class.values()))

threshold_service = ThresholdService()
