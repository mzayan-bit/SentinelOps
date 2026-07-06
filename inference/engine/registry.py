from enum import Enum
from typing import Type
import logging

from inference.engine.backend import InferenceBackend, UltralyticsBackend

logger = logging.getLogger("sentinelops.engine.registry")

class AITaskType(Enum):
    OBJECT_DETECTION = "object_detection"
    SEGMENTATION = "segmentation"
    POSE_ESTIMATION = "pose_estimation"
    OCR = "ocr"
    FACE_BLUR = "face_blur"
    LPR = "license_plate_recognition"


class TaskRegistry:
    """
    Architecture-ready registry for mapping diverse AI tasks to specific implementation 
    handlers or execution pipelines. This allows the platform to support multi-model 
    inference (e.g., running detection, then OCR on bounding boxes) without modifying 
    the core pipeline interfaces.
    """
    
    _handlers = {}

    @classmethod
    def register(cls, task_type: AITaskType, handler_class: Type[InferenceBackend]):
        """Registers an inference backend class to handle a specific AI task."""
        cls._handlers[task_type] = handler_class
        logger.info(f"[TaskRegistry] Registered {handler_class.__name__} for {task_type.value}")

    @classmethod
    def get_handler(cls, task_type: AITaskType) -> Type[InferenceBackend]:
        """Retrieves the configured backend class for a task."""
        if task_type not in cls._handlers:
            logger.warning(f"[TaskRegistry] No explicit handler for {task_type.value}. Defaulting to Object Detection.")
            return cls._handlers.get(AITaskType.OBJECT_DETECTION, UltralyticsBackend)
        return cls._handlers[task_type]

# Pre-register the standard capabilities
TaskRegistry.register(AITaskType.OBJECT_DETECTION, UltralyticsBackend)
