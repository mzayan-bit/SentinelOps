"""
SentinelOps — Task Status REST API Routes
=============================================
FastAPI router for inspecting background task status.

Endpoints:
    GET /api/tasks              — List recent tasks
    GET /api/tasks/{task_id}    — Get status of a specific task
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.security import Role, get_current_user, require_role
from app.services.task_worker import TaskStatus, task_worker

logger = logging.getLogger("sentinelops.task_api")

router = APIRouter(prefix="/api/tasks", tags=["Tasks"])


@router.get(
    "",
    summary="List recent background tasks",
)
async def list_tasks(
    status: TaskStatus | None = Query(
        default=None, description="Filter by task status"
    ),
    limit: int = Query(default=50, ge=1, le=200),
    user: User = Depends(require_role(Role.VIEWER)),
):
    """Return a list of recent background tasks with their statuses."""
    tasks = task_worker.list_tasks(status_filter=status, limit=limit)
    return [
        {
            "task_id": t.task_id,
            "task_type": t.task_type,
            "status": t.status.value,
            "submitted_at": t.submitted_at,
            "started_at": t.started_at,
            "completed_at": t.completed_at,
            "error": t.error,
        }
        for t in tasks
    ]


@router.get(
    "/{task_id}",
    summary="Get task status",
)
async def get_task_status(
    task_id: str,
    user: User = Depends(require_role(Role.VIEWER)),
):
    """Return the current status and result of a background task."""
    task = task_worker.get_status(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found.")

    response = {
        "task_id": task.task_id,
        "task_type": task.task_type,
        "status": task.status.value,
        "submitted_at": task.submitted_at,
        "started_at": task.started_at,
        "completed_at": task.completed_at,
        "error": task.error,
    }

    # Include serialisable result for completed tasks
    if task.status == TaskStatus.COMPLETED and task.result is not None:
        try:
            # If result is a Pydantic model, serialise it
            if hasattr(task.result, "model_dump"):
                response["result"] = task.result.model_dump(mode="json")
            else:
                response["result"] = task.result
        except Exception:
            response["result"] = str(task.result)

    return response
