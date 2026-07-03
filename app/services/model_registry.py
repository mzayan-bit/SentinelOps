"""
SentinelOps — Model Registry Service
======================================
Manages YOLO models dynamically.
"""

import json
import logging
from pathlib import Path
from typing import Optional

from config.settings import settings
from schemas.model_registry import RegisteredModel

logger = logging.getLogger("sentinelops.model_registry")

class ModelRegistryService:
    def __init__(self):
        self.registry_file = settings.registry_dir / "models.json"
        self._ensure_registry_exists()

    def _ensure_registry_exists(self):
        if not self.registry_file.parent.exists():
            self.registry_file.parent.mkdir(parents=True, exist_ok=True)
        if not self.registry_file.exists():
            self._save([])

    def _load(self) -> list[RegisteredModel]:
        try:
            with open(self.registry_file, "r") as f:
                data = json.load(f)
                return [RegisteredModel(**item) for item in data]
        except (json.JSONDecodeError, FileNotFoundError):
            return []

    def _save(self, models: list[RegisteredModel]):
        with open(self.registry_file, "w") as f:
            json.dump([m.model_dump() for m in models], f, indent=4)

    def register_model(self, model: RegisteredModel) -> RegisteredModel:
        models = self._load()
        # If we insert an active model, we should deactivate others
        if model.active:
            for m in models:
                m.active = False
                
        # Ensure name and version uniqueness
        for m in models:
            if m.name == model.name and m.version == model.version:
                logger.info(f"Model {model.name} v{model.version} already exists. Updating.")
                m.path = model.path
                m.description = model.description
                m.metrics = model.metrics
                if model.active:
                    m.active = True
                self._save(models)
                return m
        
        models.append(model)
        self._save(models)
        return model

    def list_models(self) -> list[RegisteredModel]:
        return self._load()

    def get_active_model(self) -> Optional[RegisteredModel]:
        for m in self._load():
            if m.active:
                return m
        return None

    def set_active_model(self, name: str, version: str) -> Optional[RegisteredModel]:
        models = self._load()
        active_model = None
        for m in models:
            if m.name == name and m.version == version:
                m.active = True
                active_model = m
            else:
                m.active = False
        
        if active_model:
            self._save(models)
            # Dynamically switch the active model
            from inference.model_loader import ModelLoader
            try:
                ModelLoader().switch_model(active_model.path)
            except Exception as e:
                logger.error(f"Failed to switch model to {active_model.path}: {e}")
                raise
        return active_model

model_registry_service = ModelRegistryService()
