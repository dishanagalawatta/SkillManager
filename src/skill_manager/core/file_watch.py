from __future__ import annotations

import threading
from collections.abc import Callable
from pathlib import Path

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer


class SkillFolderEventHandler(FileSystemEventHandler):
    """Coalescing hook point for skill-folder changes.

    Debounces rapid file-system events so that a burst of changes (e.g.
    during ``git pull``) only triggers a single callback after *debounce_ms*
    milliseconds of inactivity.  Set ``debounce_ms=0`` to disable debouncing
    (callback fires immediately on every qualifying event).
    """

    def __init__(self, callback: Callable[[str], None], debounce_ms: int = 300):
        super().__init__()
        self._callback = callback
        self._debounce_ms = debounce_ms
        self._timer: threading.Timer | None = None
        self._lock = threading.Lock()

    def on_any_event(self, event: FileSystemEvent) -> None:
        if event.is_directory or str(event.src_path).lower().endswith(".md"):
            if self._debounce_ms > 0:
                self._schedule_fire()
            else:
                self._callback(str(event.src_path))

    def _schedule_fire(self) -> None:
        with self._lock:
            if self._timer is not None:
                self._timer.cancel()
            self._timer = threading.Timer(self._debounce_ms / 1000.0, self._fire)
            self._timer.daemon = True
            self._timer.start()

    def _fire(self) -> None:
        with self._lock:
            self._timer = None
        self._callback("batch")

    def cancel(self) -> None:
        """Cancel any pending debounced callback."""
        with self._lock:
            if self._timer is not None:
                self._timer.cancel()
                self._timer = None


class SkillFolderWatcher:
    """Small watchdog wrapper so discovery can gain live refreshes incrementally."""

    def __init__(self, paths: list[str], callback: Callable[[str], None], debounce_ms: int = 300):
        self._paths = [Path(path).expanduser() for path in paths if path]
        self._handler = SkillFolderEventHandler(callback, debounce_ms=debounce_ms)
        self._observer = Observer()
        self._started = False

    def start(self) -> None:
        if self._started:
            return
        for path in self._paths:
            if path.is_dir():
                self._observer.schedule(self._handler, str(path), recursive=True)
        self._observer.start()
        self._started = True

    def stop(self) -> None:
        if not self._started:
            return
        self._handler.cancel()
        self._observer.stop()
        self._observer.join(timeout=2)
        self._started = False
