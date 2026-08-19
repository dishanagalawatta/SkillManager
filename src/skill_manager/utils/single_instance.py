"""Single-instance guard: Windows mutex + Linux PID lockfile.

Extracted from ``app.py`` during Phase 1 of the codebase refactor. The GUI and
MCP launchers share ``_app_mutex`` / ``_SINGLE_INSTANCE_LOCK_PATH`` through
this module; ``release_lock()`` is invoked from ``AppController.on_quit`` so a
second instance can start after the first shuts down.
"""

import contextlib
import os
import sys

# Windows mutex handle (``CreateMutexW`` result) or Linux lock state.
# Explicit ``None`` init — shared mutable global, reset by ``release_lock()``.
_app_mutex = None

_SINGLE_INSTANCE_LOCK_PATH: str | None = None


def _bring_existing_window_to_front() -> None:
    """Finds the existing SkillManager window and brings it to the front.

    Uses Win32 API on Windows, ``xdotool`` / ``wmctrl`` on Linux.
    Best-effort: silently no-ops when tools are unavailable.
    """
    if sys.platform == "win32":
        import ctypes

        hwnd = ctypes.windll.user32.FindWindowW(None, "Skill Manager")
        if hwnd:
            ctypes.windll.user32.ShowWindow(hwnd, 9)  # SW_RESTORE
            ctypes.windll.user32.SetForegroundWindow(hwnd)
        return

    if sys.platform == "linux":
        import shutil
        import subprocess

        xdotool = shutil.which("xdotool")
        if xdotool:
            try:
                subprocess.run(
                    [xdotool, "search", "--name", "Skill Manager", "windowactivate"],
                    capture_output=True,
                    timeout=5,
                )
                return
            except Exception:  # noqa: BLE001
                pass

        wmctrl = shutil.which("wmctrl")
        if wmctrl:
            with contextlib.suppress(Exception):
                subprocess.run(
                    [wmctrl, "-a", "Skill Manager"],
                    capture_output=True,
                    timeout=5,
                )


def _acquire_linux_lock() -> str | None:
    """Create a PID-based single-instance lock.

    Writes the current PID to a lock file.  If the file already exists
    and the PID inside it is still alive, returns ``None`` (another
    instance is running).  If the PID is stale, replaces it.

    Returns the lock file path on success, ``None`` on failure.
    """
    global _SINGLE_INSTANCE_LOCK_PATH
    from skill_manager.core.config import DATA_DIR

    lock_path = os.path.join(str(DATA_DIR), "app.lock")
    try:
        # Try reading existing lock
        if os.path.exists(lock_path):
            with open(lock_path) as f:
                old_pid_str = f.read().strip()
            if old_pid_str:
                try:
                    old_pid = int(old_pid_str)
                    # Check if process is alive
                    os.kill(old_pid, 0)  # signal 0 = existence check
                    return None  # Another instance is running
                except (OSError, ValueError):
                    pass  # Stale lock — fall through to replace
            os.remove(lock_path)

        with open(lock_path, "w") as f:
            f.write(str(os.getpid()))
        _SINGLE_INSTANCE_LOCK_PATH = lock_path
        return lock_path
    except OSError:
        return None


def release_lock() -> None:
    """Release the single-instance mutex / lockfile so another instance can start.

    Called from ``AppController.on_quit`` during shutdown. Resets both the
    Windows mutex handle and the Linux PID lockfile (if present).
    """
    global _app_mutex, _SINGLE_INSTANCE_LOCK_PATH
    _app_mutex = None
    if _SINGLE_INSTANCE_LOCK_PATH and os.path.exists(_SINGLE_INSTANCE_LOCK_PATH):
        with contextlib.suppress(OSError):
            os.remove(_SINGLE_INSTANCE_LOCK_PATH)
        _SINGLE_INSTANCE_LOCK_PATH = None
