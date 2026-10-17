"""Performance bridge functions: process metrics and startup timing."""

from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import Any

from ._telemetry import _log_call

# Captured at first import so ``measure_startup_time`` reports elapsed time
# since the bridge was loaded (a proxy for process startup).
_START_TIME = time.perf_counter()


def _iso_now() -> str:
    return datetime.now(UTC).isoformat()


def get_performance_metrics() -> dict[str, Any]:
    """Snapshot process-level performance metrics (memory, CPU, threads)."""
    _log_call("get_performance_metrics")
    try:
        import psutil  # type: ignore[import-not-found]

        process = psutil.Process()
        mem_mb = process.memory_info().rss / (1024.0 * 1024.0)
        cpu_percent = process.cpu_percent(interval=0.0)
        thread_count = process.num_threads()
        pid = process.pid
        uptime_seconds = time.time() - process.create_time()
        return {
            "ok": True,
            "memory_mb": round(float(mem_mb), 2),
            "cpu_percent": round(float(cpu_percent), 2),
            "thread_count": int(thread_count),
            "process_id": int(pid),
            "uptime_seconds": round(float(uptime_seconds), 2),
            "error": None,
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "memory_mb": 0.0,
            "cpu_percent": 0.0,
            "thread_count": 0,
            "process_id": 0,
            "uptime_seconds": 0.0,
            "error": str(exc),
        }


def measure_startup_time() -> dict[str, Any]:
    """Measure application startup time (elapsed since bridge load)."""
    _log_call("measure_startup_time")
    try:
        startup_ms = (time.perf_counter() - _START_TIME) * 1000.0
        return {
            "ok": True,
            "startup_ms": round(float(startup_ms), 2),
            "timestamp": _iso_now(),
            "error": None,
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "startup_ms": 0.0,
            "timestamp": _iso_now(),
            "error": str(exc),
        }
