"""
Task runner abstraction to allow switching between background and synchronous execution.
"""

import asyncio
import threading
from collections.abc import Callable
from typing import Any

try:
    from PySide6 import QtAsyncio
except Exception:  # pragma: no cover - depends on installed PySide6 build
    QtAsyncio = None


class TaskRunner:
    """Base class for task execution strategies."""

    def run(self, target: Callable, args: tuple = (), kwargs: dict = None) -> Any:
        """Executes the target with provided arguments."""
        raise NotImplementedError

    def submit(
        self,
        target: Callable,
        callback: Callable[[Any], None] = None,
        args: tuple = (),
        kwargs: dict = None,
    ) -> None:
        """Executes the target and optionally receives its result."""

        def wrapped():
            result = target(*(args or ()), **(kwargs or {}))
            if callback:
                callback(result)
            return result

        return self.run(wrapped)


class BackgroundTaskRunner(TaskRunner):
    """Executes tasks in a background daemon thread."""

    def run(self, target: Callable, args: tuple = (), kwargs: dict = None) -> None:
        kwargs = kwargs or {}
        threading.Thread(target=target, args=args, kwargs=kwargs, daemon=True).start()


class QtAsyncioTaskRunner(TaskRunner):
    """Runs coroutine tasks on QtAsyncio when the Qt event loop owns async work."""

    def run(self, target: Callable, args: tuple = (), kwargs: dict = None) -> Any:
        kwargs = kwargs or {}
        result = target(*args, **kwargs)
        if asyncio.iscoroutine(result):
            if QtAsyncio is None:
                return asyncio.run(result)
            return asyncio.ensure_future(result)
        return result


class SynchronousTaskRunner(TaskRunner):
    """Executes tasks synchronously in the current thread. Useful for testing."""

    def run(self, target: Callable, args: tuple = (), kwargs: dict = None) -> Any:
        kwargs = kwargs or {}
        return target(*args, **kwargs)
