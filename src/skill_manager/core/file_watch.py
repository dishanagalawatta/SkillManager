"""File system watcher using watchdog (lazy-loaded).

Architecture:
- ``SkillFolderEventHandler`` inherits from watchdog's ``FileSystemEventHandler``
  (required at class definition time for proper event dispatch)
- ``Observer`` is lazy-imported in ``SkillFolderWatcher.__init__`` to defer
  the native-extension load until the watcher is actually constructed
- Graceful degradation: if watchdog is unavailable, the watcher silently
  no-ops on ``start()`` instead of crashing the import chain
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

from watchdog.events import FileSystemEventHandler

if TYPE_CHECKING:
    from watchdog.events import FileSystemEvent

logger = logging.getLogger(__name__)


class SkillFolderEventHandler(FileSystemEventHandler):
    """Coalescing hook point for skill-folder changes.

    Debounces rapid file-system events so that a burst of changes (e.g.
    during ``git pull``) only triggers a single callback after *debounce_ms*
    milliseconds of inactivity.  Set ``debounce_ms=0`` to disable debouncing
    (callback fires immediately on every qualifying event).

    Qualifying events:
    - Directory events (create, delete, move)
    - ``.md`` file events (create, modify, delete)
    - Explicit ``deleted`` or ``moved`` events (always fire, even for
      non-``.md`` files — catches edge cases where watchdog reports
      folder deletions as non-directory events on Windows)
    """

    def __init__(self, callback: Callable[[str], None], debounce_ms: int = 300):
        super().__init__()
        self._callback = callback
        self._debounce_ms = debounce_ms
        self._timer: threading.Timer | None = None
        self._lock = threading.Lock()

    def on_any_event(self, event: FileSystemEvent) -> None:
        if event.is_directory or str(event.src_path).lower().endswith(".md"):
            self._fire_or_schedule(event)

    def on_deleted(self, event: FileSystemEvent) -> None:
        # Always fire on deletions — catches skill-folder removal even
        # when watchdog reports it as a non-directory event on Windows.
        self._fire_or_schedule(event)

    def on_moved(self, event: FileSystemEvent) -> None:
        # Always fire on moves/renames — catches folder renames.
        self._fire_or_schedule(event)

    def _fire_or_schedule(self, event: FileSystemEvent) -> None:
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
    """Per-directory (non-recursive) watchdog wrapper for skill-folder changes.

    Watches individual directories rather than using recursive watching.
    On Windows, recursive watching is unreliable — it can miss events in
    deeply nested directories or stop firing entirely after certain
    operations.  Per-directory watching avoids these issues.

    Provides ``add_path`` / ``remove_path`` so the application can
    dynamically register discovered skill directories after initial startup.
    """

    def __init__(self, paths: list[str], callback: Callable[[str], None], debounce_ms: int = 300):
        self._paths = [Path(path).expanduser() for path in paths if path]
        self._handler = SkillFolderEventHandler(callback, debounce_ms=debounce_ms)
        self.started = False
        self._observer = None  # type: ignore[assignment]
        try:
            from watchdog.observers import Observer

            self._observer = Observer()
        except (ImportError, OSError) as e:
            logger.warning("watchdog unavailable: %s. Folder watching disabled.", e)

    def start(self) -> None:
        if self.started or self._observer is None:
            return
        for path in self._paths:
            if path.is_dir():
                self._observer.schedule(self._handler, str(path), recursive=False)
        self._observer.start()
        self.started = True

    def add_path(self, path: str) -> None:
        """Register a directory for watching (non-recursive).

        Safe to call multiple times with the same path — watchdog
        deduplicates internally.  No-op if the observer is not running
        or the path does not exist.
        """
        if not self.started or self._observer is None:
            return
        p = Path(path).expanduser()
        if p.is_dir():
            self._observer.schedule(self._handler, str(p), recursive=False)

    def remove_path(self, path: str) -> None:
        """Unregister a directory from watching.

        Best-effort: watchdog does not expose a clean per-path unschedule
        API, so we log the intent.  The watcher naturally stops firing
        events when the directory no longer exists.
        """
        logger.debug("remove_path requested (best-effort): %s", path)

    def stop(self) -> None:
        if not self.started or self._observer is None:
            return
        self._handler.cancel()
        self._observer.stop()
        self._observer.join(timeout=2)
        self.started = False
