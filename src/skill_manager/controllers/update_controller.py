"""
Purpose: Manages skill updates, synchronization, and scanning.
Usage: Accessed via AppController.updates
"""

import threading

from PySide6.QtCore import QTimer

from skill_manager.controllers.base import BaseController
from skill_manager.core.analytics import capture_event
from skill_manager.core.update_service import UpdateService


class UpdateController(BaseController):
    """Controller for skill updates and synchronization."""

    def update_now(self):
        """Starts a global update of all skills and projects."""
        self.app._set_status("Starting global update...")

        # Mark projects as syncing
        for p in self.app._projects:
            if p not in self.app._syncing_projects:
                self.app._syncing_projects.append(p)
        self.app.projectsChanged.emit()

        # Mark sources as updating
        for s in self.app._update_packages:
            s["is_updating"] = True
            s["just_finished"] = False
        self.app.updatePackagesChanged.emit()

        service = UpdateService(
            sources=self.app._sources,
            projects=self.app._projects,
            update_packages=self.app._update_packages,
            project_aliases=self.app._project_aliases,
            task_runner=self.app.task_runner,
        )

        def source_progress_callback(idx, data):
            def update_item():
                self.app._update_packages[idx] = data
                self.app.updatePackagesChanged.emit()

            QTimer.singleShot(0, self.app, update_item)

        def completion_callback(result, _updated_sources):
            def finalize():
                self.app.load_initial_data()
                msg = (
                    f"Global update complete: {result['merged']} updated, {result['failed']} failed"
                )
                self.app._set_status(msg)
                
                # Capture analytics
                capture_event(
                    "skill_package_updated",
                    {"source_type": "global", "success": result["failed"] == 0},
                )

                self.config.set("skills", self.app._update_packages)
                self.app._syncing_projects = []
                self.app.projectsChanged.emit()

            QTimer.singleShot(0, self.app, finalize)

        service.run_global_update(
            status_callback=self.app._set_status,
            source_progress_callback=source_progress_callback,
            completion_callback=completion_callback,
        )

    def scan_for_updates(self):
        """Scans all sources and projects for potential updates."""
        self.app._set_status("Scanning for updates...")
        self.app._is_loading = True
        self.app.isLoadingChanged.emit()

        service = UpdateService(
            sources=self.app._sources,
            projects=self.app._projects,
            update_packages=self.app._update_packages,
            project_aliases=self.app._project_aliases,
            task_runner=self.app.task_runner,
        )

        def completion_callback(results, updated_sources):
            def finalize():
                self.app._update_results = results
                self.app._update_packages = updated_sources
                self.recalculate_stats()
                self.app._is_loading = False
                self.app.isLoadingChanged.emit()
                self.app.updatePackagesChanged.emit()
                self.app._set_status(f"Scan complete: {len(results)} skills processed")

            QTimer.singleShot(0, self.app, finalize)

        service.scan_for_updates(
            status_callback=self.app._set_status, completion_callback=completion_callback
        )

    def update_skill_in_project(self, skill_name: str, project_name: str):
        """Updates a specific skill in a specific project."""
        self.app._set_status(f"Updating {skill_name} in {project_name}...")

        def run_surgical_sync():
            try:
                # 1. Find source skill
                source_skill = next(
                    (
                        s
                        for s in self.app._library_model._all_skills
                        if s.get("is_source") and s.get("name") == skill_name
                    ),
                    None,
                )
                if not source_skill:
                    self.app._set_status(f"Error: Could not find source skill {skill_name}")
                    return

                # 2. Find project path
                project_path = next(
                    (p for p in self.app._projects if self.app.getProjectLabel(p) == project_name),
                    None,
                )
                if not project_path:
                    self.app._set_status(f"Error: Could not find project {project_name}")
                    return

                # 3. Perform copy
                from skill_manager.core.copier import copy_skill_folders_to_projects

                result = copy_skill_folders_to_projects(
                    [source_skill], [project_path], update_only=True
                )

                msg = f"Updated {skill_name} in {project_name}"
                if result["failed"] > 0:
                    msg = f"Failed to update {skill_name} in {project_name}"

                QTimer.singleShot(0, self.app, lambda: self.app._set_status(msg))
                QTimer.singleShot(500, self.app, self.scan_for_updates)
            except Exception as e:
                err_msg = f"Surgical update failed: {e}"
                capture_exception(e)
                QTimer.singleShot(0, self.app, lambda: self.app._set_status(err_msg))

        self.app.task_runner.run(run_surgical_sync)

    def recalculate_stats(self):
        """Recalculates the up-to-date/outdated/missing stats."""
        up_to_date = 0
        outdated = 0
        missing = 0
        for item in self.app._update_results:
            if item["status"] == "up_to_date":
                up_to_date += 1
            elif item["status"] == "outdated":
                outdated += 1
            elif item["status"] == "missing":
                missing += 1

        self.app._stats_up_to_date = up_to_date
        self.app._stats_outdated = outdated
        self.app._stats_missing = missing
        self.app.statsChanged.emit()
