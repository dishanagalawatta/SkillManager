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
from skill_manager.core.schemas import CacheState, SkillRecord

logger = logging.getLogger(__name__)


class DiscoveryController(BaseController):
    """Controller for background skill discovery and cache handling."""

    # Simplified signal using the CacheState Pydantic model and a finality flag
    _discoverySuccess = Signal(object, bool)
    _discoveryError = Signal(str)

    def __init__(self, app):
        super().__init__(app)
        self._discoverySuccess.connect(self._finalize_loading)
        self._discoveryError.connect(self._handle_loading_error)
        self._previous_skills: dict[str, SkillRecord] = {}  # path -> SkillRecord

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

    def _run_discovery_sync(self) -> dict | CacheState:
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

            def cache_callback(cached_data_dict):
                try:
                    # Validate cache data through Pydantic
                    cache_state = CacheState.model_validate(cached_data_dict)
                    logger.info(
                        "[CACHE] Loading %d skills from cache...",
                        len(cache_state.skills),
                    )
                    # Dispatch UI update safely to the main thread via Signal
                    self._discoverySuccess.emit(cache_state, False)
                except Exception as ve:
                    logger.error("[CACHE] Validation failed: %s", ve)

            result_dict = service.discover_all(cache_callback=cache_callback)

            # Final validation
            if "error" in result_dict:
                return result_dict

            return CacheState.model_validate(result_dict)

        except Exception as e:
            traceback.print_exc()
            return {"error": str(e)}

    def _on_discovery_done(self, result: dict | CacheState):
        if not result:
            return
        if isinstance(result, dict) and "error" in result:
            self._discoveryError.emit(f"Error scanning skills: {result['error']}")
            return

        # result is a validated CacheState
        self._discoverySuccess.emit(result, True)

    @Slot(object, bool)
    def _finalize_loading(self, state: CacheState, is_final: bool = True):
        """Updates model and UI state on the main thread after discovery completes.

        Uses incremental model updates when possible: only changed skills are
        re-indexed, avoiding a full SearchEngine rebuild.
        """
        if self.app._categories != state.categories:
            self.app._categories = state.categories
            self.app.categoriesChanged.emit()

        # Build a lookup of new skills by path
        new_skills_map = {s.local_path: s for s in state.skills if s.local_path}

        # Determine which skills changed since last scan
        added_or_updated: list[dict] = []
        for path, skill in new_skills_map.items():
            prev = self._previous_skills.get(path)
            if prev is None or prev != skill:
                added_or_updated.append(skill.model_dump())

        removed_paths = set(self._previous_skills.keys()) - set(new_skills_map.keys())

        if self._previous_skills and (added_or_updated or removed_paths):
            # Incremental update — only touch changed skills
            if added_or_updated:
                self.app._library_model.addOrUpdateSkills(added_or_updated)
                self.app._quick_copy_model.addOrUpdateSkills(added_or_updated)
            if removed_paths:
                self.app._library_model.removeSkillsByPath(list(removed_paths))
                self.app._quick_copy_model.removeSkillsByPath(list(removed_paths))
            logger.info(
                "[DISCOVERY] Incremental update: %d added/updated, %d removed",
                len(added_or_updated),
                len(removed_paths),
            )
        else:
            # First load or full replacement needed
            skills_dump = [s.model_dump() for s in state.skills]
            self.app._library_model.setSkills(skills_dump)
            self.app._quick_copy_model.setSkills(skills_dump)

        # Snapshot current state for next diff
        self._previous_skills = new_skills_map

        # Ensure client filters are set
        self.app._library_model.clientFilter = self.app._client_format
        self.app._quick_copy_model.clientFilter = self.app._client_format

        # Apply the shared current project filter to QuickCopy model
        if self.app._current_project_label:
            self.app._quick_copy_model.projectFilter = self.app._current_project_label

        self.app._set_status(state.status)

        if is_final:
            self.app._is_loading = False
            self.app.isLoadingChanged.emit()

    def _handle_loading_error(self, error_msg):
        """Handles discovery errors on the main thread."""
        self.app._set_status(error_msg)
        self.app._is_loading = False
        self.app.isLoadingChanged.emit()
