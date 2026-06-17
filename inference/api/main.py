"""
SentinelOps — FastAPI Inference Service
=========================================
Production-ready inference API for YOLO object detection models.

Endpoints:
    POST /predict-image    — Single image inference
    POST /predict-batch    — Batch inference (multiple images)
    GET  /health           — Service health check
    GET  /model-info       — Loaded model metadata

Run::

    uvicorn inference.api.main:app --host 0.0.0.0 --port 8000 --reload

Environment variables (or .env):
    MODEL_PATH     — Path to YOLO .pt weights  (default: models/best.pt)
    CONFIDENCE     — Default confidence threshold (default: 0.25)
    INPUT_SIZE     — Model input size           (default: 640)
    DEVICE         — cpu | cuda | mps           (default: auto)
"""

from __future__ import annotations

import io
import logging
import os
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import numpy as np
from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from PIL import Image

from inference.api.schemas import (
    BatchPredictionResponse,
    BoundingBox,
    Detection,
    ErrorResponse,
    HealthResponse,
    ModelInfoResponse,
    PredictionResponse,
)

load_dotenv()

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("sentinelops.inference")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
MODEL_PATH: str = os.getenv("MODEL_PATH", "models/best.pt")
DEFAULT_CONFIDENCE: float = float(os.getenv("CONFIDENCE", "0.25"))
INPUT_SIZE: int = int(os.getenv("INPUT_SIZE", "640"))
DEVICE: str = os.getenv("DEVICE", "auto")

# ---------------------------------------------------------------------------
# Global state
# ---------------------------------------------------------------------------
_state: dict[str, Any] = {
    "model": None,
    "model_name": None,
    "class_names": [],
    "start_time": None,
}


# ---------------------------------------------------------------------------
# Model loader
# ---------------------------------------------------------------------------
def _load_model() -> None:
    """Load the YOLO model into global state (called once at startup)."""
    model_path = Path(MODEL_PATH)

    if not model_path.exists():
        logger.warning(
            "Model weights not found at '%s'. "
            "The service will start but /predict endpoints will return errors "
            "until a valid model is provided.",
            model_path,
        )
        return

    try:
        from ultralytics import YOLO

        device = DEVICE if DEVICE != "auto" else None
        model = YOLO(str(model_path))

        if device:
            model.to(device)

        _state["model"] = model
        _state["model_name"] = model_path.stem
        _state["class_names"] = list(model.names.values()) if hasattr(model, "names") else []

        logger.info(
            "Model loaded: %s (%d classes, device=%s)",
            model_path,
            len(_state["class_names"]),
            device or "auto",
        )
    except Exception:
        logger.exception("Failed to load model from '%s'.", model_path)


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    logger.info("SentinelOps inference service starting …")
    _state["start_time"] = time.time()
    _load_model()
    yield
    logger.info("SentinelOps inference service shutting down.")


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="SentinelOps Inference API",
    description=(
        "Production-grade YOLO object detection inference service. "
        "Upload images and receive structured detection results."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
    responses={
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Exception handlers
# ---------------------------------------------------------------------------
@app.exception_handler(Exception)
async def global_exception_handler(request, exc: Exception):
    logger.exception("Unhandled exception: %s", exc)
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="Internal server error",
            detail=str(exc),
        ).model_dump(),
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _ensure_model() -> None:
    """Raise 503 if the model is not loaded."""
    if _state["model"] is None:
        raise HTTPException(
            status_code=503,
            detail=(
                f"Model not loaded. Ensure weights exist at '{MODEL_PATH}' "
                "and restart the service."
            ),
        )


async def _read_image(file: UploadFile) -> Image.Image:
    """Read an uploaded file into a PIL Image."""
    contents = await file.read()
    try:
        img = Image.open(io.BytesIO(contents)).convert("RGB")
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid image file '{file.filename}': {exc}",
        ) from exc
    return img


def _run_inference(
    img: Image.Image,
    confidence: float,
) -> PredictionResponse:
    """Run YOLO inference on a single PIL image and build a response."""
    model = _state["model"]
    class_names: list[str] = _state["class_names"]

    img_array = np.asarray(img)
    h, w = img_array.shape[:2]

    t0 = time.perf_counter()
    results = model.predict(
        source=img_array,
        conf=confidence,
        imgsz=INPUT_SIZE,
        verbose=False,
    )
    elapsed_ms = (time.perf_counter() - t0) * 1000

    detections: list[Detection] = []
    if results and len(results) > 0:
        result = results[0]
        boxes = result.boxes

        for box in boxes:
            xyxy = box.xyxy[0].tolist()
            cls_id = int(box.cls[0].item())
            conf = float(box.conf[0].item())

            x_min, y_min, x_max, y_max = xyxy
            detections.append(
                Detection(
                    class_id=cls_id,
                    class_name=class_names[cls_id] if cls_id < len(class_names) else f"class_{cls_id}",
                    confidence=round(conf, 4),
                    bbox=BoundingBox(
                        x_min=round(x_min, 2),
                        y_min=round(y_min, 2),
                        x_max=round(x_max, 2),
                        y_max=round(y_max, 2),
                        width=round(x_max - x_min, 2),
                        height=round(y_max - y_min, 2),
                    ),
                )
            )

    return PredictionResponse(
        image_width=w,
        image_height=h,
        num_detections=len(detections),
        detections=detections,
        inference_time_ms=round(elapsed_ms, 2),
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["System"],
    summary="Service health check",
)
async def health():
    """Returns service status, model state, and uptime."""
    uptime = time.time() - _state["start_time"] if _state["start_time"] else 0
    return HealthResponse(
        status="healthy",
        model_loaded=_state["model"] is not None,
        model_name=_state["model_name"],
        uptime_seconds=round(uptime, 2),
    )


@app.get(
    "/model-info",
    response_model=ModelInfoResponse,
    tags=["System"],
    summary="Loaded model metadata",
    responses={503: {"model": ErrorResponse}},
)
async def model_info():
    """Returns details about the currently loaded YOLO model."""
    _ensure_model()
    model = _state["model"]

    device = str(next(model.model.parameters()).device) if hasattr(model, "model") else "unknown"

    return ModelInfoResponse(
        model_name=_state["model_name"] or "unknown",
        model_path=MODEL_PATH,
        num_classes=len(_state["class_names"]),
        class_names=_state["class_names"],
        input_size=INPUT_SIZE,
        device=device,
    )


@app.post(
    "/predict-image",
    response_model=PredictionResponse,
    tags=["Inference"],
    summary="Single image inference",
    responses={
        400: {"model": ErrorResponse, "description": "Invalid image"},
        503: {"model": ErrorResponse, "description": "Model not loaded"},
    },
)
async def predict_image(
    file: UploadFile = File(..., description="Image file (JPEG / PNG)"),
    confidence: float = Query(
        default=DEFAULT_CONFIDENCE,
        ge=0.01,
        le=1.0,
        description="Minimum confidence threshold",
    ),
):
    """Upload a single image and receive structured detection results.

    Returns bounding boxes, class names, and confidence scores for
    every detection above the confidence threshold.
    """
    _ensure_model()

    logger.info(
        "predict-image | file=%s  confidence=%.2f",
        file.filename,
        confidence,
    )

    img = await _read_image(file)
    response = _run_inference(img, confidence)

    logger.info(
        "predict-image | file=%s  detections=%d  time=%.1fms",
        file.filename,
        response.num_detections,
        response.inference_time_ms,
    )
    return response


@app.post(
    "/predict-batch",
    response_model=BatchPredictionResponse,
    tags=["Inference"],
    summary="Batch image inference",
    responses={
        400: {"model": ErrorResponse, "description": "Invalid image(s)"},
        503: {"model": ErrorResponse, "description": "Model not loaded"},
    },
)
async def predict_batch(
    files: list[UploadFile] = File(..., description="One or more image files"),
    confidence: float = Query(
        default=DEFAULT_CONFIDENCE,
        ge=0.01,
        le=1.0,
        description="Minimum confidence threshold",
    ),
):
    """Upload multiple images and receive batched detection results.

    Each image is processed independently and results are returned
    in the same order as the uploaded files.
    """
    _ensure_model()

    if not files:
        raise HTTPException(status_code=400, detail="No files provided.")

    logger.info(
        "predict-batch | files=%d  confidence=%.2f",
        len(files),
        confidence,
    )

    t0 = time.perf_counter()
    results: list[PredictionResponse] = []

    for f in files:
        img = await _read_image(f)
        result = _run_inference(img, confidence)
        results.append(result)

    total_ms = (time.perf_counter() - t0) * 1000

    logger.info(
        "predict-batch | files=%d  total_detections=%d  time=%.1fms",
        len(files),
        sum(r.num_detections for r in results),
        total_ms,
    )

    return BatchPredictionResponse(
        total_images=len(results),
        results=results,
        total_inference_time_ms=round(total_ms, 2),
    )
