"""
Purpose: Manages background discovery of skills and cache synchronization.
Usage: Accessed via AppController.discovery
"""

import asyncio
import logging
import os
import traceback

import PySide6.QtAsyncio as QtAsyncio
from PySide6.QtCore import Slot

from skill_manager.controllers.base import BaseController
from skill_manager.core.discovery import DiscoveryService

logger = logging.getLogger(__name__)


class DiscoveryController(BaseController):
    """Controller for background skill discovery and cache handling."""

    @Slot()
    def loadInitialData(self):
        """Initial scan of skills on application startup using QtAsyncio."""
        QtAsyncio.run(self._do_discovery())

    async def _do_discovery(self):
        """Internal async discovery implementation."""
        self.app._is_loading = True
        self.app.isLoadingChanged.emit()
        self.app._set_status("Scanning skills...")
        used_cache_preview = False

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
                nonlocal used_cache_preview
                used_cache_preview = True
                logger.info(f"[CACHE] Loading {len(cached_data.get('skills', []))} skills from cache...")
                # Update UI immediately from the cached data
                self._finalize_loading(
                    cached_data.get("skills", []),
                    cached_data.get("projects", []),
                    cached_data.get("categories", []),
                    cached_data.get("project_labels", []),
                    f"Loaded {len(cached_data.get('skills', []))} skills from cache (Refreshing...)",
                    is_final=False,
                )

            # run_in_executor allows running CPU-bound discovery without blocking the event loop
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(
                None, lambda: service.discover_all(cache_callback=cache_callback)
            )

            # In tests, we skip the artificial delay
            if used_cache_preview and not self.app.isTesting:
                await asyncio.sleep(0.2)

            self._finalize_loading(
                result["skills"],
                result["projects"],
                result["categories"],
                result["project_labels"],
                result["status"],
                is_final=True,
            )
        except Exception as e:
            error_msg = f"Error scanning skills: {e}"
            traceback.print_exc()
            self._handle_loading_error(error_msg)

    def _finalize_loading(self, all_skills, _projects_state, cats, proj_labels, status, is_final=True):
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
