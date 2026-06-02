from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer


class SkillFolderEventHandler(FileSystemEventHandler):
    """Coalescing hook point for skill-folder changes."""

    def __init__(self, callback: Callable[[str], None]):
        super().__init__()
        self._callback = callback

    def on_any_event(self, event: FileSystemEvent) -> None:
        if event.is_directory or str(event.src_path).lower().endswith(".md"):
            self._callback(str(event.src_path))


class SkillFolderWatcher:
    """Small watchdog wrapper so discovery can gain live refreshes incrementally."""

    def __init__(self, paths: list[str], callback: Callable[[str], None]):
        self._paths = [Path(path).expanduser() for path in paths if path]
        self._handler = SkillFolderEventHandler(callback)
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
        self._observer.stop()
        self._observer.join(timeout=2)
        self._started = False
