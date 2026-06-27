"""
SentinelOps — Task Worker Tests
==================================
Verifies the background task worker: submission, status tracking,
error handling, filtering, and graceful shutdown.
"""

import time

import pytest

from app.services.task_worker import TaskResult, TaskStatus, TaskWorker


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def worker():
    """Create a fresh TaskWorker for each test with 2 threads."""
    w = TaskWorker(max_workers=2)
    yield w
    w.shutdown(wait=True)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
def test_submit_returns_task_id(worker: TaskWorker):
    """submit() should return a unique string task ID."""
    task_id = worker.submit(lambda: "hello", task_type="test")
    assert isinstance(task_id, str)
    assert task_id.startswith("TASK-")


def test_task_completes_successfully(worker: TaskWorker):
    """A successful task should transition to COMPLETED with a result."""

    def slow_add(a, b):
        time.sleep(0.05)
        return a + b

    task_id = worker.submit(slow_add, 3, 7, task_type="addition")

    # Wait for completion
    for _ in range(20):
        result = worker.get_status(task_id)
        if result and result.status == TaskStatus.COMPLETED:
            break
        time.sleep(0.05)

    assert result is not None
    assert result.status == TaskStatus.COMPLETED
    assert result.result == 10
    assert result.error is None
    assert result.completed_at is not None
    assert result.completed_at >= result.submitted_at


def test_task_failure_captures_error(worker: TaskWorker):
    """A failing task should transition to FAILED with an error message."""

    def broken():
        raise ValueError("something went wrong")

    task_id = worker.submit(broken, task_type="broken_task")

    for _ in range(20):
        result = worker.get_status(task_id)
        if result and result.status == TaskStatus.FAILED:
            break
        time.sleep(0.05)

    assert result is not None
    assert result.status == TaskStatus.FAILED
    assert "something went wrong" in result.error
    assert result.completed_at is not None


def test_get_status_unknown_task(worker: TaskWorker):
    """get_status() returns None for unknown task IDs."""
    assert worker.get_status("TASK-nonexistent") is None


def test_list_tasks_returns_all(worker: TaskWorker):
    """list_tasks() should return all submitted tasks."""
    worker.submit(lambda: 1, task_type="t1")
    worker.submit(lambda: 2, task_type="t2")
    worker.submit(lambda: 3, task_type="t3")

    # Wait briefly for all to complete
    time.sleep(0.2)

    tasks = worker.list_tasks()
    assert len(tasks) == 3


def test_list_tasks_filter_by_status(worker: TaskWorker):
    """list_tasks(status_filter=...) should only return matching tasks."""

    def slow():
        time.sleep(0.3)
        return "done"

    worker.submit(slow, task_type="slow")
    worker.submit(lambda: "fast", task_type="fast")

    # Give the fast one time to finish but not the slow one
    time.sleep(0.1)

    completed = worker.list_tasks(status_filter=TaskStatus.COMPLETED)
    assert all(t.status == TaskStatus.COMPLETED for t in completed)


def test_task_type_is_recorded(worker: TaskWorker):
    """The task_type label should be preserved on the TaskResult."""
    task_id = worker.submit(lambda: None, task_type="report_generation")
    result = worker.get_status(task_id)
    assert result.task_type == "report_generation"


def test_shutdown_waits_for_inflight(worker: TaskWorker):
    """shutdown(wait=True) should let in-flight tasks finish."""
    results = []

    def append_result():
        time.sleep(0.1)
        results.append("done")

    worker.submit(append_result, task_type="inflight")
    worker.shutdown(wait=True)

    assert results == ["done"]
