"""
Purpose: Manages skill updates, synchronization, and scanning.
Usage: Accessed via AppController.updates
"""


from PySide6.QtCore import QTimer

from skill_manager.controllers.base import BaseController
from skill_manager.core.analytics import capture_event, capture_exception
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

    def add_update_package(self, package_name: str):
        """Adds a basic NPM-style source."""
        if not package_name:
            return
        new_source = {
            "name": package_name,
            "source_type": "npm",
            "package_name": package_name,
            "last_updated": "Never",
            "is_updating": False,
        }
        self.app._update_packages.append(new_source)
        self.config.set("skills", self.app._update_packages)
        self.app.updatePackagesChanged.emit()
        self.app._set_status(f"Added update package: {package_name}")

    def add_skill_package(self, data: dict):
        """Adds a fully configured skill package (git/npm/custom)."""
        if not data:
            return
        from skill_manager.core.skill_packages import (
            check_skill_package_versions,
            normalize_skill_package_config,
        )

        new_source = normalize_skill_package_config(data)
        new_source["is_updating"] = False
        new_source["last_updated"] = "Never"

        # Immediate version check
        new_source = check_skill_package_versions(new_source)

        self.app._update_packages.append(new_source)
        self.config.set("skills", self.app._update_packages)
        self.app.updatePackagesChanged.emit()
        self.app._set_status(f"Added skill package: {new_source.get('name')}")
        capture_event(
            "skill_package_added", {"source_type": new_source.get("source_type", "unknown")}
        )

    def update_update_package(self, index: int, data: dict):
        """Updates configuration for an existing skill package."""
        if 0 <= index < len(self.app._update_packages):
            # Preserve internal state
            is_updating = self.app._update_packages[index].get("is_updating", False)

            from skill_manager.core.skill_packages import (
                check_skill_package_versions,
                normalize_skill_package_config,
            )

            updated_source = normalize_skill_package_config(data)
            updated_source["is_updating"] = is_updating

            # Refresh versions
            updated_source = check_skill_package_versions(updated_source)

            self.app._update_packages[index] = updated_source
            self.config.set("skills", self.app._update_packages)
            self.app.updatePackagesChanged.emit()
            self.app._set_status(f"Updated skill package: {updated_source.get('name')}")

    def remove_update_package(self, index: int):
        """Removes a skill package."""
        if 0 <= index < len(self.app._update_packages):
            source = self.app._update_packages.pop(index)
            self.config.set("skills", self.app._update_packages)
            self.app.updatePackagesChanged.emit()
            self.app._set_status(f"Removed update package: {source.get('name')}")
            capture_event(
                "skill_package_removed", {"source_type": source.get("source_type", "unknown")}
            )

    def run_package_update(self, index: int):
        """Runs update for a single skill package."""
        if 0 <= index < len(self.app._update_packages):
            source = self.app._update_packages[index]
            source["is_updating"] = True
            source["just_finished"] = False
            self.app.updatePackagesChanged.emit()
            self.app._set_status(f"Updating {source.get('name')}...")

            def run():
                from datetime import datetime
                from pathlib import Path
                from skill_manager.core.skill_packages import run_skill_package_update

                try:
                    pkg_path = source.get("package_path") or source.get("local_path")
                    if not pkg_path and self.app._sources:
                        potential_path = self.app._sources[0]
                        if Path(potential_path).resolve() == Path.cwd().resolve():
                            source["package_path"] = str(Path(potential_path) / ".agents" / "skills")
                        else:
                            source["package_path"] = potential_path
                    else:
                        source["package_path"] = pkg_path

                    def log_callback(msg):
                        QTimer.singleShot(0, self.app, lambda: self.app._set_status(msg))

                    updated_source = run_skill_package_update(source, log_callback)
                    source.update(updated_source)
                    source["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M")
                    capture_event("skill_package_updated", {"source_type": source.get("source_type", "unknown"), "success": True})
                except Exception as e:
                    capture_event("skill_package_updated", {"source_type": source.get("source_type", "unknown"), "success": False})
                    capture_exception(e)
                    err_msg = f"Update failed for {source.get('name')}: {e}"
                    QTimer.singleShot(0, self.app, lambda: self.app._set_status(err_msg))
                finally:
                    def finalize_ui():
                        source["is_updating"] = False
                        source["just_finished"] = True
                        self.app._update_packages[index] = dict(source)
                        self.app.updatePackagesChanged.emit()
                        self.app._set_status(f"Update finished for {source.get('name')}")
                        self.app.load_initial_data()
                        self.config.set("skills", self.app._update_packages)
                    QTimer.singleShot(0, self.app, finalize_ui)

            self.app.task_runner.run(run)

    def sync_project(self, path: str):
        """Synchronizes and updates all skills in a specific project."""
        if path not in self.app._projects:
            return

        self.app._set_status(f"Updating {self.app.getProjectLabel(path)}...")
        if path not in self.app._syncing_projects:
            self.app._syncing_projects.append(path)
            self.app.projectsChanged.emit()

        def run_sync():
            try:
                from skill_manager.core.quick_copy import discover_package_skills
                from skill_manager.core.parsing import parse_skill_md, categorize_skill, build_skill_search_text

                source_skills = discover_package_skills(
                    sources=self.app._sources,
                    parse_skill_md=parse_skill_md,
                    categorize_skill=categorize_skill,
                    build_search_text=build_skill_search_text,
                )

                from skill_manager.core.copier import copy_skill_folders_to_projects
                result = copy_skill_folders_to_projects(source_skills, [path], update_only=True)

                msg = f"Update complete for {self.app.getProjectLabel(path)}: {result['merged']} updated, {result['failed']} failed"
                QTimer.singleShot(0, self.app, lambda: self.app._set_status(msg))
            except Exception as e:
                err_msg = f"Update failed for {path}: {e}"
                QTimer.singleShot(0, self.app, lambda: self.app._set_status(err_msg))
            finally:
                if path in self.app._syncing_projects:
                    self.app._syncing_projects.remove(path)
                QTimer.singleShot(0, self.app, self.app.projectsChanged.emit)

        self.app.task_runner.run(run_sync)
