import logging
import mlflow
from typing import Optional
from config.settings import settings
from schemas.model_registry import RegisteredModel, DeploymentLog

logger = logging.getLogger("sentinelops.mlflow")

class MLflowIntegrationService:
    def __init__(self):
        self.tracking_uri = settings.mlflow_tracking_uri
        self.experiment_name = "SentinelOps_Enterprise_Models"
        try:
            mlflow.set_tracking_uri(self.tracking_uri)
            mlflow.set_experiment(self.experiment_name)
            self._enabled = True
            logger.info(f"MLflow Integration initialized at {self.tracking_uri}")
        except Exception as e:
            logger.warning(f"MLflow Integration failed: {e}. Running in degraded mode.")
            self._enabled = False

    def sync_model_registration(self, model: RegisteredModel):
        if not self._enabled:
            return
            
        try:
            with mlflow.start_run(run_name=f"{model.name}_{model.version}"):
                # Log Parameters
                mlflow.log_param("model_name", model.name)
                mlflow.log_param("model_version", model.version)
                mlflow.log_param("author", model.author)
                mlflow.log_param("dataset", model.dataset)
                mlflow.log_param("environment", model.environment.value)
                mlflow.log_param("hardware", model.hardware)
                
                # Log Metrics
                mlflow.log_metric("precision", model.precision)
                mlflow.log_metric("recall", model.recall)
                mlflow.log_metric("mAP", model.mAP)
                mlflow.log_metric("latency_ms", model.latency)
                mlflow.log_metric("fps", model.fps)
                
                for k, v in model.metrics.items():
                    if isinstance(v, (int, float)):
                        mlflow.log_metric(k, float(v))
                        
                # Log tags
                mlflow.set_tag("status", model.status)
                mlflow.set_tag("classes", ",".join(model.classes))
                
        except Exception as e:
            logger.error(f"Failed to sync model {model.name} to MLflow: {e}")

    def sync_deployment_event(self, log: DeploymentLog):
        if not self._enabled:
            return
            
        try:
            # We log deployments as separate runs or nested runs. We will just create a quick run to log the event.
            with mlflow.start_run(run_name=f"DEPLOY_{log.model_name}_{log.version}_{log.environment.value}"):
                mlflow.log_param("event", "DEPLOYMENT")
                mlflow.log_param("target_env", log.environment.value)
                mlflow.log_param("user", log.user)
                mlflow.log_param("status", log.status)
                mlflow.set_tag("notes", log.notes)
        except Exception as e:
            logger.error(f"Failed to sync deployment to MLflow: {e}")

mlflow_integration = MLflowIntegrationService()
