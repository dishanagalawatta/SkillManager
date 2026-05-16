"""
Purpose: Manages skill sources, project targets, and configuration state.
Usage: Accessed via AppController.config_mgr
"""
import os

from skill_manager.controllers.base import BaseController
from skill_manager.core.analytics import capture_event


class ConfigController(BaseController):
    """Controller for project configuration and sources."""

    def add_source(self, url: str):
        """Adds a local skill source directory."""
        path = url.replace("file:///", "").replace("/", "\\") if url.startswith("file://") else url
        if path not in self.app._sources:
            self.app._sources.append(path)
            self.config.set("sources", self.app._sources)
            self.app.sourcesChanged.emit()
            self.app._set_status(f"Added source: {path}")

    def remove_source(self, path: str):
        """Removes a local skill source directory."""
        if path in self.app._sources:
            self.app._sources.remove(path)
            self.config.set("sources", self.app._sources)
            self.app.sourcesChanged.emit()
            self.app._set_status(f"Removed source: {path}")

    def add_target(self, url: str):
        """Adds a project target directory."""
        path = url.replace("file:///", "").replace("/", "\\") if url.startswith("file://") else url
        if path not in self.app._targets:
            self.app._targets.append(path)
            self.config.set("targets", self.app._targets)
            self.app.targetsChanged.emit()
            self.app._set_status(f"Added target: {path}")
            capture_event("project_target_added", {"target_count": len(self.app._targets)})

    def remove_target(self, path: str):
        """Removes a project target directory."""
        if path in self.app._targets:
            self.app._targets.remove(path)
            if path in self.app._syncing_targets:
                self.app._syncing_targets.remove(path)
            # Also remove alias if it exists
            if path in self.app._target_aliases:
                del self.app._target_aliases[path]
                self.config.set("target_aliases", self.app._target_aliases)
            self.config.set("targets", self.app._targets)
            self.app.targetsChanged.emit()
            self.app._set_status(f"Removed target: {path}")

    def get_target_label(self, path: str) -> str:
        """Returns the human-readable label for a target path."""
        if not path:
            return ""
        norm_path = path.replace("\\", "/")
        label = self.app._target_aliases.get(path) or self.app._target_aliases.get(norm_path)
        if not label:
            # os.path.basename doesn't work for Windows paths on Linux, so we do it manually or convert it
            label = os.path.basename(norm_path)
        return label

    def set_target_alias(self, path: str, alias: str):
        """Sets a custom alias for a project target."""
        if not path:
            return
        if not alias:
            if path in self.app._target_aliases:
                del self.app._target_aliases[path]
        else:
            self.app._target_aliases[path] = alias

        self.config.set("target_aliases", self.app._target_aliases)
        self.app.targetsChanged.emit()
        self.app.refreshSkills()
        self.app._set_status(f"Renamed project to: {alias or 'Default'}")

    def verify_git_source(self, url: str, token: str = None) -> str:
        """Verifies a git repository and returns its latest tag."""
        if not url:
            return ""
        from skill_manager.core.skill_sources import get_git_tag
        self.app._set_status(f"Verifying repository: {url}")
        tag = get_git_tag(url, is_remote=True, token=token)
        if tag:
            self.app._set_status(f"Repository verified. Latest version: {tag}")
        else:
            self.app._set_status(f"Verification failed for: {url}")
        return tag or ""
