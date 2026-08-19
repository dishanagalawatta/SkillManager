"""Tests for the cooperative file lock (cooperative_lock.py)."""

import threading
import time
from pathlib import Path

import pytest

from skill_manager.utils.cooperative_lock import FileLock, LockTimeout


class TestFileLock:
    """Tests for FileLock acquire/release."""

    def test_acquire_and_release(self, tmp_path: Path):
        """FileLock can be acquired and released."""
        lock_path = tmp_path / "test.lock"
        lock = FileLock(lock_path, timeout=1.0)
        lock.acquire()
        assert lock._fd is not None
        lock.release()
        assert lock._fd is None

    def test_context_manager(self, tmp_path: Path):
        """FileLock works as a context manager."""
        lock_path = tmp_path / "test.lock"
        with FileLock(lock_path, timeout=1.0) as lock:
            assert lock._fd is not None
        assert lock._fd is None

    def test_lock_timeout(self, tmp_path: Path):
        """FileLock raises LockTimeout when lock cannot be acquired."""
        lock_path = tmp_path / "test.lock"

        # Hold the lock in a background thread
        def hold_lock():
            with FileLock(lock_path, timeout=1.0):
                time.sleep(0.5)

        t = threading.Thread(target=hold_lock)
        t.start()
        time.sleep(0.05)  # Let the lock be acquired

        # Try to acquire with a very short timeout
        with pytest.raises(LockTimeout), FileLock(lock_path, timeout=0.1):
            pass

        t.join()

    def test_reentrant_lock(self, tmp_path: Path):
        """Same thread can re-acquire the lock after releasing."""
        lock_path = tmp_path / "test.lock"
        lock = FileLock(lock_path, timeout=1.0)
        lock.acquire()
        lock.release()
        # Should be able to acquire again
        lock.acquire()
        lock.release()

    def test_sequential_locks(self, tmp_path: Path):
        """Sequential lock acquisitions work correctly."""
        lock_path = tmp_path / "test.lock"
        for _ in range(3):
            with FileLock(lock_path, timeout=1.0):
                pass  # Just verify it doesn't hang

    def test_different_lock_files(self, tmp_path: Path):
        """Different lock files don't interfere with each other."""
        lock1_path = tmp_path / "lock1.lock"
        lock2_path = tmp_path / "lock2.lock"

        with FileLock(lock1_path, timeout=1.0), FileLock(lock2_path, timeout=1.0):
            pass
