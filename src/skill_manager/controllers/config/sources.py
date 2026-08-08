"""Skill source management for the ConfigController facade."""

import logging
import os
from pathlib import Path

from PySide6.QtCore import Slot

from skill_manager.core.analytics import capture_event, capture_exception
from skill_manager.core.diagnostics import get_diagnostic_logger

logger = logging.getLogger(__name__)


class SourcesMixin:
    """Source directory CRUD plus git-package verification."""

    def normalize_path(self, raw_url: str) -> str:
        """Helper to convert file URLs or raw strings to canonical absolute local paths."""
        from skill_manager.core.copier import url_to_local_path

        return url_to_local_path(raw_url)

    @Slot(str)
    def addSource(self, url: str):
        """Adds a local skill source directory with path validation."""
        if not url or not str(url).strip():
            return
        resolved_path = self.normalize_path(url)
        if not resolved_path:
            return

        p = Path(resolved_path)
        if not p.is_dir() and os.environ.get("SKILL_MANAGER_SKIP_INITIAL_LOAD") != "1":
            msg = f"Source directory does not exist: {resolved_path}"
            logger.warning("[CONFIG] %s", msg)
            self.app._set_status(msg)
            get_diagnostic_logger().log_event(
                "WARNING",
                "source_add_invalid_path",
                msg,
                data={"raw_input": url, "resolved_path": resolved_path},
            )
            return

        try:
            if resolved_path not in self.app._sources:
                self.app._sources.append(resolved_path)
                self.config.set("sources", self.app._sources)
                self.app.sourcesChanged.emit()
                self.app._set_status(f"Added source: {resolved_path}")
                capture_event("skill_package_added", {"source_type": "local"})
                self._refresh_after_source_add(resolved_path)
        except Exception as e:
            self.app._set_status(f"Failed to add source: {e}")
            capture_exception(e)

    def _refresh_after_source_add(self, source_path: str) -> None:
        """Register the new source with the file watcher and trigger a silent
        background discovery refresh so its skills appear without restart."""
        try:
            watcher = getattr(self.app, "_watcher", None)
            if watcher is not None:
                watcher.add_path(source_path)
        except Exception as exc:
            logger.warning("[CONFIG] Failed to register watcher path: %s", exc)

        try:
            refresh = getattr(self.app, "loadInitialData", None)
            if refresh is not None:
                refresh()
        except Exception as exc:
            logger.warning("[CONFIG] Failed to trigger discovery refresh: %s", exc)

    @Slot(str)
    def removeSource(self, path: str):
        """Removes a local skill source directory."""
        if path in self.app._sources:
            self.app._sources.remove(path)
            self.config.set("sources", self.app._sources)
            self.app.sourcesChanged.emit()
            self.app._set_status(f"Removed source: {path}")
            capture_event("skill_package_removed", {"source_type": "local"})

    @Slot(int)
    def removeSourceByIndex(self, index: int):
        """Removes a local skill source directory by its index in the list."""
        if 0 <= index < len(self.app._sources):
            self.removeSource(self.app._sources[index])

    @Slot(str, str, result=str)
    def verifyGitPackage(self, url: str, token: str | None = None) -> str:
        """Verifies a git repository and returns its latest tag."""
        if not url:
            return ""
        from skill_manager.core.skill_packages import get_git_tag

        self.app._set_status(f"Verifying repository: {url}")
        tag = get_git_tag(url, is_remote=True, token=token)
        if tag:
            self.app._set_status(f"Repository verified. Latest version: {tag}")
        else:
            self.app._set_status(f"Verification failed for: {url}")
        return tag or ""
