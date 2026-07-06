"""
SentinelOps — Enterprise Model Registry Service
================================================
Manages YOLO models, deployment lifecycles, and MLflow sync.
"""

import json
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any

from config.settings import settings
from schemas.model_registry import RegisteredModel, DeploymentLog, Environment
from app.services.mlflow_integration import mlflow_integration

logger = logging.getLogger("sentinelops.model_registry")

class ModelRegistryService:
    def __init__(self):
        self.registry_file = settings.registry_dir / "models.json"
        self.deployments_file = settings.registry_dir / "deployments.json"
        self._ensure_registry_exists()

    def _ensure_registry_exists(self):
        if not self.registry_file.parent.exists():
            self.registry_file.parent.mkdir(parents=True, exist_ok=True)
        if not self.registry_file.exists():
            self._save([])
        if not self.deployments_file.exists():
            self._save_deployments([])

    def _load(self) -> List[RegisteredModel]:
        try:
            with open(self.registry_file, "r") as f:
                data = json.load(f)
                return [RegisteredModel(**item) for item in data]
        except (json.JSONDecodeError, FileNotFoundError):
            return []

    def _save(self, models: List[RegisteredModel]):
        with open(self.registry_file, "w") as f:
            json.dump([m.model_dump() for m in models], f, indent=4)
            
    def _load_deployments(self) -> List[DeploymentLog]:
        try:
            with open(self.deployments_file, "r") as f:
                data = json.load(f)
                return [DeploymentLog(**item) for item in data]
        except (json.JSONDecodeError, FileNotFoundError):
            return []
            
    def _save_deployments(self, logs: List[DeploymentLog]):
        with open(self.deployments_file, "w") as f:
            json.dump([l.model_dump() for l in logs], f, indent=4)
            
    def _log_deployment(self, log: DeploymentLog):
        logs = self._load_deployments()
        logs.append(log)
        self._save_deployments(logs)
        mlflow_integration.sync_deployment_event(log)

    def register_model(self, model: RegisteredModel) -> RegisteredModel:
        models = self._load()
        
        # Ensure name and version uniqueness
        updated = False
        for m in models:
            if m.name == model.name and m.version == model.version:
                logger.info(f"Model {model.name} v{model.version} already exists. Updating metadata.")
                # We do not overwrite environment or active status directly here to prevent accidental prod wipes
                m.description = model.description
                m.metrics = model.metrics
                m.precision = model.precision
                m.recall = model.recall
                m.mAP = model.mAP
                m.latency = model.latency
                m.fps = model.fps
                updated = True
                model = m
                break
        
        if not updated:
            models.append(model)
            
        self._save(models)
        mlflow_integration.sync_model_registration(model)
        
        self._log_deployment(DeploymentLog(
            model_name=model.name,
            version=model.version,
            environment=model.environment,
            notes="Model registered in system"
        ))
        return model

    def list_models(self) -> List[RegisteredModel]:
        return self._load()

    def get_active_model(self) -> Optional[RegisteredModel]:
        for m in self._load():
            if m.active and m.environment == Environment.PRODUCTION:
                return m
        return None

    def set_active_model(self, name: str, version: str) -> Optional[RegisteredModel]:
        # This is essentially hot-loading into PRODUCTION
        models = self._load()
        active_model = None
        for m in models:
            if m.name == name and m.version == version:
                m.active = True
                m.environment = Environment.PRODUCTION
                active_model = m
            else:
                m.active = False
        
        if not active_model:
            raise ValueError(f"Model {name} v{version} not found in registry.")
            
        # Dynamically switch the active model with health verification!
        from inference.model_loader import ModelLoader
        try:
            ModelLoader().switch_model(active_model.path)
            # Switch was successful! Save registry.
            self._save(models)
            
            self._log_deployment(DeploymentLog(
                model_name=active_model.name,
                version=active_model.version,
                environment=Environment.PRODUCTION,
                notes="Hot loaded into Production"
            ))
            return active_model
        except Exception as e:
            logger.error(f"Health Verification Failed for {active_model.path}: {e}")
            # Do NOT save models list, rollback is automatic!
            self._log_deployment(DeploymentLog(
                model_name=active_model.name,
                version=active_model.version,
                environment=Environment.PRODUCTION,
                status="FAILED",
                notes=f"Health check failed: {str(e)}"
            ))
            raise RuntimeError(f"Model rejected due to failing Health Verification: {e}")

    def promote_model(self, name: str, version: str, target_env: Environment, notes: str = "") -> RegisteredModel:
        models = self._load()
        target_model = None
        
        for m in models:
            if m.name == name and m.version == version:
                m.environment = target_env
                target_model = m
                break
                
        if not target_model:
            raise ValueError(f"Model {name} v{version} not found in registry.")
            
        self._save(models)
        
        # Log to deployment history & MLflow
        self._log_deployment(DeploymentLog(
            model_name=target_model.name,
            version=target_model.version,
            environment=target_env,
            notes=f"Promoted: {notes}"
        ))
        mlflow_integration.sync_model_registration(target_model)
        
        # If promoting straight to production, we trigger hot-loading safely via set_active_model
        if target_env == Environment.PRODUCTION:
            return self.set_active_model(name, version)
            
        return target_model

    def rollback_model(self) -> RegisteredModel:
        """Rolls back to the most recently successful Production model."""
        logs = self._load_deployments()
        # Find the last SUCCESSFUL production deployment that is NOT the currently active one
        active = self.get_active_model()
        
        for log in reversed(logs):
            if log.environment == Environment.PRODUCTION and log.status == "SUCCESS":
                if active and log.model_name == active.name and log.version == active.version:
                    continue # Skip the currently active one
                    
                logger.info(f"Rolling back to {log.model_name} v{log.version}")
                # We found the previous good one!
                return self.set_active_model(log.model_name, log.version)
                
        raise ValueError("No historical production model found to rollback to.")
        
    def compare_models(self, name_a: str, version_a: str, name_b: str, version_b: str) -> Dict[str, Any]:
        """Compares metadata and metrics of two models."""
        models = self._load()
        ma = next((m for m in models if m.name == name_a and m.version == version_a), None)
        mb = next((m for m in models if m.name == name_b and m.version == version_b), None)
        
        if not ma or not mb:
            raise ValueError("One or both models not found.")
            
        return {
            "model_a": f"{ma.name} v{ma.version}",
            "model_b": f"{mb.name} v{mb.version}",
            "precision_diff": mb.precision - ma.precision,
            "recall_diff": mb.recall - ma.recall,
            "map_diff": mb.mAP - ma.mAP,
            "latency_diff_ms": mb.latency - ma.latency,
            "fps_diff": mb.fps - ma.fps
        }

    def get_deployment_history(self) -> List[DeploymentLog]:
        return self._load_deployments()

model_registry_service = ModelRegistryService()

