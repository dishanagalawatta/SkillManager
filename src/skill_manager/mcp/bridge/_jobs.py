"""Fire-and-forget async job dispatch with a job_id result buffer."""

from __future__ import annotations

import threading
import uuid
from collections.abc import Callable
from typing import Any

from ._controller import _controller_or_none
from ._telemetry import _log_call

# Async job result buffers keyed by job_id.
_JOBS: dict[str, dict[str, Any]] = {}


# ---------------------------------------------------------------------------
# Async job dispatch (fire-and-forget via BackgroundTaskRunner)
# ---------------------------------------------------------------------------
def run_async_job(func: Callable[..., Any], *args: Any, **kwargs: Any) -> str:
    """Dispatch ``func`` on a background thread, returning a job_id.

    ``BackgroundTaskRunner.run`` is fire-and-forget (returns None), so we keep
    our own result buffer keyed by ``job_id``. Use :func:`get_job` to poll.
    """
    _log_call("run_async_job")
    job_id = uuid.uuid4().hex
    _JOBS[job_id] = {
        "job_id": job_id,
        "status": "running",
        "result": None,
        "error": None,
    }

    def _wrapper() -> None:
        try:
            result = func(*args, **kwargs)
            _JOBS[job_id]["result"] = result
            _JOBS[job_id]["status"] = "done"
        except Exception as exc:  # noqa: BLE001
            _JOBS[job_id]["error"] = str(exc)
            _JOBS[job_id]["status"] = "error"

    try:
        controller = _controller_or_none()
        if controller is not None and hasattr(controller, "task_runner"):
            controller.task_runner.run(_wrapper)  # type: ignore[arg-type]
        else:
            # Fallback: run in a plain daemon thread if no controller.
            threading.Thread(target=_wrapper, daemon=True).start()
    except Exception as exc:  # noqa: BLE001
        _JOBS[job_id]["error"] = str(exc)
        _JOBS[job_id]["status"] = "error"

    return job_id


def get_job(job_id: str) -> dict[str, Any] | None:
    """Return the job buffer for ``job_id`` (or None if unknown)."""
    _log_call("get_job")
    return _JOBS.get(job_id)
