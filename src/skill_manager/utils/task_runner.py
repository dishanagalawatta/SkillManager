"""
Task runner abstraction to allow switching between background and synchronous execution.
"""

import asyncio
import logging
import threading
from collections.abc import Callable
from typing import Any

try:
    from PySide6 import QtAsyncio
except Exception:  # pragma: no cover - depends on installed PySide6 build
    QtAsyncio = None

logger = logging.getLogger(__name__)


class TaskRunner:
    """Base class for task execution strategies."""

    def run(self, target: Callable, args: tuple = (), kwargs: dict | None = None) -> Any:
        """Executes the target with provided arguments."""
        raise NotImplementedError

    def shutdown(self, timeout: float = 2.0) -> None:
        """Join background threads.  No-op for synchronous runners."""

    def submit(
        self,
        target: Callable,
        callback: Callable[[Any], None] | None = None,
        args: tuple = (),
        kwargs: dict | None = None,
    ) -> None:
        """Executes the target and optionally receives its result."""

        def wrapped():
            result = target(*(args or ()), **(kwargs or {}))
            if callback:
                callback(result)
            return result

        return self.run(wrapped)


class BackgroundTaskRunner(TaskRunner):
    """Executes tasks in a background daemon thread.

    Tracks spawned threads and provides a ``shutdown()`` method that joins
    them within a bounded timeout — useful for controlled shutdown before
    the interpreter exits.
    """

    def __init__(self) -> None:
        self._threads: list[threading.Thread] = []
        self._lock = threading.Lock()

    def run(self, target: Callable, args: tuple = (), kwargs: dict | None = None) -> None:
        kwargs = kwargs or {}
        t = threading.Thread(target=target, args=args, kwargs=kwargs, daemon=True)
        t.start()
        with self._lock:
            self._threads.append(t)

    def shutdown(self, timeout: float = 2.0) -> None:
        """Join all tracked threads within *timeout* seconds.

        Non-daemon threads that don't exit in time are left to the interpreter.
        """
        with self._lock:
            threads = list(self._threads)
            self._threads.clear()

        for t in threads:
            if t.is_alive():
                t.join(timeout=timeout / max(len(threads), 1))
                if t.is_alive():
                    logger.debug(
                        "BackgroundTaskRunner: thread %s did not exit within timeout",
                        t.name,
                    )


class QtAsyncioTaskRunner(TaskRunner):
    """Runs coroutine tasks on QtAsyncio when the Qt event loop owns async work."""

    def run(self, target: Callable, args: tuple = (), kwargs: dict | None = None) -> Any:
        kwargs = kwargs or {}
        result = target(*args, **kwargs)
        if asyncio.iscoroutine(result):
            if QtAsyncio is None:
                return asyncio.run(result)
            return asyncio.ensure_future(result)
        return result


class SynchronousTaskRunner(TaskRunner):
    """Executes tasks synchronously in the current thread. Useful for testing."""

    def run(self, target: Callable, args: tuple = (), kwargs: dict | None = None) -> Any:
        kwargs = kwargs or {}
        return target(*args, **kwargs)
