"""Cross-platform file lock for coordinating multi-instance access to shared files.

Uses ``msvcrt.locking`` on Windows and ``fcntl.flock`` on POSIX.
Provides a ``FileLock`` context manager that blocks until the lock
is acquired, with a configurable timeout (default 5 seconds).

When the lock cannot be acquired within the timeout, ``LockTimeoutError``
is raised so callers can fall back to stale data instead of blocking
indefinitely.

Important: The lock is released *before* returning from ``__exit__`` or
``release()``.  On Windows, ``msvcrt.locking`` holds the file descriptor
open, which can block ``os.replace`` calls on nearby files.  The lock
is always released before any file rename/move operations.
"""

from __future__ import annotations

import logging
import os
import time
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 5.0  # seconds
POLL_INTERVAL = 0.05  # 50 ms between retries


class LockTimeoutError(Exception):
    """Raised when a file lock cannot be acquired within the timeout."""


# Backwards-compatible alias
LockTimeout = LockTimeoutError


class FileLock:
    """Cross-platform file-based lock.

    Usage::

        with FileLock("cache.json.lock"):
            # safe to read/write cache.json here
            ...

    The lock file is created alongside the target file (``<path>.lock``).
    If the lock cannot be acquired within *timeout* seconds, a
    ``LockTimeoutError`` is raised.
    """

    def __init__(self, lock_path: str | Path, *, timeout: float = DEFAULT_TIMEOUT) -> None:
        self._lock_path = Path(str(lock_path) + ".lock")
        self._timeout = timeout
        self._fd: int | None = None

    def acquire(self) -> None:
        deadline = time.monotonic() + self._timeout
        while True:
            try:
                self._fd = os.open(str(self._lock_path), os.O_CREAT | os.O_RDWR, 0o666)
                if os.name == "nt":
                    import msvcrt

                    msvcrt.locking(self._fd, msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(self._fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                return  # lock acquired
            except OSError:
                if self._fd is not None:
                    os.close(self._fd)
                    self._fd = None
                if time.monotonic() >= deadline:
                    raise LockTimeoutError(
                        f"Could not acquire lock {self._lock_path} within {self._timeout}s"
                    ) from None
                time.sleep(POLL_INTERVAL)

    def release(self) -> None:
        if self._fd is None:
            return
        try:
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(self._fd, msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(self._fd, fcntl.LOCK_UN)
        except OSError:
            logger.debug("Error releasing lock %s", self._lock_path, exc_info=True)
        finally:
            os.close(self._fd)
            self._fd = None

    def __enter__(self) -> FileLock:
        self.acquire()
        return self

    def __exit__(self, *_exc: object) -> None:
        self.release()
