"""
Purpose: Manages background discovery of skills and cache synchronization.
Usage: Accessed via AppController.discovery
"""

import logging
import os
import traceback

from PySide6.QtCore import Signal, Slot

from skill_manager.controllers.base import BaseController
from skill_manager.core.discovery import DiscoveryService

logger = logging.getLogger(__name__)


class DiscoveryController(BaseController):
    """Controller for background skill discovery and cache handling."""

    _discoverySuccess = Signal(list, list, list, list, str, bool)
    _discoveryError = Signal(str)

    def __init__(self, app):
        super().__init__(app)
        self._discoverySuccess.connect(self._finalize_loading)
        self._discoveryError.connect(self._handle_loading_error)

    @Slot()
    def loadInitialData(self):
        """Initial scan of skills on application startup."""
        self.app._is_loading = True
        self.app.isLoadingChanged.emit()
        self.app._set_status("Scanning skills...")

        if hasattr(self.app, "task_runner"):
            self.app.task_runner.submit(self._run_discovery_sync, self._on_discovery_done)
        else:
            import threading

            threading.Thread(
                target=lambda: self._on_discovery_done(self._run_discovery_sync())
            ).start()

    def _run_discovery_sync(self):
        """Internal synchronous discovery implementation run in a background thread."""
        discovery_sources = list(self.app._sources)
        for src in self.app._update_packages:
            pkg_path = src.get("package_path") or src.get("local_path")
            if pkg_path and os.path.exists(pkg_path) and pkg_path not in discovery_sources:
                discovery_sources.append(pkg_path)

        service = DiscoveryService(
            sources=discovery_sources,
            projects=self.app._projects,
            archive_paths=self.app._archive_paths,
            starred_paths=self.app._starred_paths,
            project_aliases=self.app._project_aliases,
        )

        try:

            def cache_callback(cached_data):
                logger.info(
                    f"[CACHE] Loading {len(cached_data.get('skills', []))} skills from cache..."
                )
                # Dispatch UI update safely to the main thread via Signal
                self._discoverySuccess.emit(
                    cached_data.get("skills", []),
                    cached_data.get("projects", []),
                    cached_data.get("categories", []),
                    cached_data.get("project_labels", []),
                    f"Loaded {len(cached_data.get('skills', []))} skills from cache (Refreshing...)",
                    False,
                )

            result = service.discover_all(cache_callback=cache_callback)

            if not self.app.isTesting:
                import time

                time.sleep(0.2)

            return result
        except Exception as e:
            traceback.print_exc()
            return {"error": str(e)}

    def _on_discovery_done(self, result):
        if not result:
            return
        if "error" in result:
            self._discoveryError.emit(f"Error scanning skills: {result['error']}")
            return

        self._discoverySuccess.emit(
            result["skills"],
            result["projects"],
            result["categories"],
            result["project_labels"],
            result["status"],
            True,
        )

    @Slot(list, list, list, list, str, bool)
    def _finalize_loading(
        self, all_skills, _projects_state, cats, proj_labels, status, is_final=True
    ):
        """Updates model and UI state on the main thread after discovery completes."""
        del proj_labels

        if self.app._categories != cats:
            self.app._categories = cats
            self.app.categoriesChanged.emit()

        # Update both models with the shared skill list
        self.app._library_model.setSkills(all_skills)
        self.app._quick_copy_model.setSkills(all_skills)

        # Ensure client filters are set
        self.app._library_model.clientFilter = self.app._client_format
        self.app._quick_copy_model.clientFilter = self.app._client_format

        if self.app.ui._default_project_filter == "all":
            self.app._library_model.projectFilter = ""
            self.app._quick_copy_model.projectFilter = ""

        self.app._set_status(status)

        if is_final:
            self.app._is_loading = False
            self.app.isLoadingChanged.emit()

    def _handle_loading_error(self, error_msg):
        """Handles discovery errors on the main thread."""
        self.app._set_status(error_msg)
        self.app._is_loading = False
        self.app.isLoadingChanged.emit()
