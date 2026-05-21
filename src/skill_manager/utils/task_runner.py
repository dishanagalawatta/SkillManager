"""
Task runner abstraction to allow switching between background and synchronous execution.
"""

import threading
from collections.abc import Callable
from typing import Any


class TaskRunner:
    """Base class for task execution strategies."""

    def run(self, target: Callable, args: tuple = (), kwargs: dict = None) -> Any:
        """Executes the target with provided arguments."""
        raise NotImplementedError


class BackgroundTaskRunner(TaskRunner):
    """Executes tasks in a background daemon thread."""

    def run(self, target: Callable, args: tuple = (), kwargs: dict = None) -> None:
        kwargs = kwargs or {}
        threading.Thread(target=target, args=args, kwargs=kwargs, daemon=True).start()


class SynchronousTaskRunner(TaskRunner):
    """Executes tasks synchronously in the current thread. Useful for testing."""

    def run(self, target: Callable, args: tuple = (), kwargs: dict = None) -> Any:
        kwargs = kwargs or {}
        return target(*args, **kwargs)
