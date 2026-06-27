"""
SentinelOps — Background Task Worker
========================================
In-process thread-pool executor for offloading heavy I/O work
(report generation, snapshot saves, video encoding) from the
request/response cycle.

Usage::

    from app.services.task_worker import task_worker

    task_id = task_worker.submit(some_function, arg1, arg2)
    result  = task_worker.get_status(task_id)
"""

from __future__ import annotations

import enum
import logging
import threading
import time
import uuid
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any, Callable

logger = logging.getLogger("sentinelops.task_worker")


# ---------------------------------------------------------------------------
# Task status enum
# ---------------------------------------------------------------------------
class TaskStatus(str, enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


# ---------------------------------------------------------------------------
# Task result container
# ---------------------------------------------------------------------------
@dataclass
class TaskResult:
    task_id: str
    task_type: str
    status: TaskStatus
    submitted_at: float
    started_at: float | None = None
    completed_at: float | None = None
    result: Any = None
    error: str | None = None


# ---------------------------------------------------------------------------
# Task Worker
# ---------------------------------------------------------------------------
class TaskWorker:
    """Manages a pool of background worker threads.

    Parameters
    ----------
    max_workers : int
        Maximum number of concurrent background threads.
    """

    def __init__(self, max_workers: int = 4) -> None:
        self._max_workers = max_workers
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="sentinelops-worker",
        )
        self._tasks: dict[str, TaskResult] = {}
        self._futures: dict[str, Future] = {}
        self._lock = threading.Lock()
        logger.info("TaskWorker initialised with %d workers", max_workers)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def submit(
        self,
        fn: Callable[..., Any],
        *args: Any,
        task_type: str = "generic",
        **kwargs: Any,
    ) -> str:
        """Submit a callable for background execution.

        Returns
        -------
        str
            A unique task ID that can be used to poll status.
        """
        task_id = f"TASK-{uuid.uuid4().hex[:12]}"
        now = time.time()

        task_result = TaskResult(
            task_id=task_id,
            task_type=task_type,
            status=TaskStatus.PENDING,
            submitted_at=now,
        )

        with self._lock:
            self._tasks[task_id] = task_result

        future = self._executor.submit(self._run, task_id, fn, *args, **kwargs)
        with self._lock:
            self._futures[task_id] = future

        logger.info("Submitted task %s (type=%s)", task_id, task_type)
        return task_id

    def get_status(self, task_id: str) -> TaskResult | None:
        """Return the current status of a task, or None if unknown."""
        with self._lock:
            return self._tasks.get(task_id)

    def list_tasks(
        self,
        status_filter: TaskStatus | None = None,
        limit: int = 50,
    ) -> list[TaskResult]:
        """List recent tasks, optionally filtered by status."""
        with self._lock:
            tasks = list(self._tasks.values())
        if status_filter is not None:
            tasks = [t for t in tasks if t.status == status_filter]
        # Most recent first
        tasks.sort(key=lambda t: t.submitted_at, reverse=True)
        return tasks[:limit]

    def shutdown(self, wait: bool = True) -> None:
        """Gracefully shut down the thread pool.

        After shutdown the worker is automatically re-initialised so the
        module-level singleton remains usable across FastAPI test client
        lifespan cycles.

        Parameters
        ----------
        wait : bool
            If True, block until all in-flight tasks finish.
        """
        logger.info("TaskWorker shutting down (wait=%s) …", wait)
        self._executor.shutdown(wait=wait)
        # Re-create the pool so the singleton stays functional
        self._executor = ThreadPoolExecutor(
            max_workers=self._max_workers,
            thread_name_prefix="sentinelops-worker",
        )
        logger.info("TaskWorker shut down complete.")

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------
    def _run(
        self,
        task_id: str,
        fn: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Wrapper executed inside the thread pool."""
        with self._lock:
            task = self._tasks[task_id]
            task.status = TaskStatus.RUNNING
            task.started_at = time.time()

        try:
            result = fn(*args, **kwargs)
            with self._lock:
                task.status = TaskStatus.COMPLETED
                task.completed_at = time.time()
                task.result = result
            logger.info("Task %s completed successfully", task_id)
            return result
        except Exception as exc:
            with self._lock:
                task.status = TaskStatus.FAILED
                task.completed_at = time.time()
                task.error = str(exc)
            logger.exception("Task %s failed: %s", task_id, exc)
            raise


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------
task_worker = TaskWorker()
