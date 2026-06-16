"""
Purpose: Manages skill updates, synchronization, and scanning.
Usage: Accessed via AppController.updates
"""

import logging
from pathlib import Path

from PySide6.QtCore import QTimer, Slot

from skill_manager.controllers.base import BaseController
from skill_manager.core.analytics import capture_event, capture_exception
from skill_manager.core.schemas import UpdatePackageRecord
from skill_manager.core.update_service import UpdateService
from skill_manager.utils.qt_threading import schedule_on_ui_thread

logger = logging.getLogger(__name__)


class UpdateController(BaseController):
    """Controller for skill updates and synchronization."""

    def _resolvePackageStorageState(self):
        """Internal helper to refresh package state from config."""
        from skill_manager.core.persistence import load_package_skill_inventory
        from skill_manager.core.skill_packages import (
            normalize_skill_package_config,
            resolve_package_storage,
        )

        packages = []
        for package in self.app._update_packages:
            try:
                # Ensure each package in memory is a valid record
                normalized = normalize_skill_package_config(package)
                record = UpdatePackageRecord.model_validate({**normalized, **package})
                packages.append(record.model_dump())
            except Exception as e:
                logger.error("Failed to normalize package during storage resolution: %s", e)

        self.app._update_packages = resolve_package_storage(
            packages, load_package_skill_inventory()
        )
        self.config.set("skills", self.app._update_packages)

    @Slot()
    def updateNow(self):
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
                if 0 <= idx < len(self.app._update_packages):
                    self.app._update_packages[idx] = data
                    self.app.updatePackagesChanged.emit()

            QTimer.singleShot(0, self.app, update_item)

        def completion_callback(result, _updated_sources):
            def finalize():
                self.app.loadInitialData()
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

    @Slot()
    def scanForUpdates(self):
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
                self.recalculateStats()
                self.app._is_loading = False
                self.app.isLoadingChanged.emit()
                self.app.updatePackagesChanged.emit()
                self.app._set_status(f"Scan complete: {len(results)} skills processed")

                # Handle Silent Auto-Update
                if (
                    self.config.get("skill_package_auto_update", True)
                    and self.config.get("skill_package_auto_update_mode") == "silent"
                    and self.app._stats_outdated > 0
                ):
                    logger.info("Silent auto-update triggered for outdated skill packages.")
                    self.updateNow()

            QTimer.singleShot(0, self.app, finalize)

        service.scan_for_updates(
            status_callback=self.app._set_status, completion_callback=completion_callback
        )

    @Slot(str, str)
    def updateSkillInProject(self, skill_name: str, project_name: str):
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

                schedule_on_ui_thread(self.app, lambda: self.app._set_status(msg))
                schedule_on_ui_thread(self.app, self.scanForUpdates, delay_ms=500)
            except Exception as e:
                err_msg = f"Surgical update failed: {e}"
                capture_exception(e)
                schedule_on_ui_thread(self.app, lambda: self.app._set_status(err_msg))

        self.app.task_runner.run(run_surgical_sync)

    @Slot()
    def recalculateStats(self):
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

    @Slot(str)
    def addUpdatePackage(self, package_name: str):
        """Adds a basic NPX-style source."""
        if not package_name:
            return
        try:
            record = UpdatePackageRecord(
                name=package_name,
                source_type="npx",
                package_name=package_name,
            )
            self.app._update_packages.append(record.model_dump())
            self.config.set("skills", self.app._update_packages)
            self.app.updatePackagesChanged.emit()
            self.app._set_status(f"Added update package: {package_name}")
        except Exception as e:
            logger.error("Failed to add update package: %s", e)
            self.app._set_status(f"Error adding package: {e}")

    @Slot(dict)
    def addSkillPackage(self, data: dict):
        """Adds a fully configured skill package (git/npx/custom)."""
        if not data:
            return
        from skill_manager.core.skill_packages import (
            check_skill_package_versions,
            normalize_skill_package_config,
        )

        try:
            # 1. Normalize and Validate
            normalized = normalize_skill_package_config(data)
            record = UpdatePackageRecord.model_validate(normalized)
            record.is_updating = False
            record.last_updated = "Never"

            # 2. Version Check (returns dict, so we re-validate)
            checked_data = check_skill_package_versions(record.model_dump())
            final_record = UpdatePackageRecord.model_validate(checked_data)

            # 3. Commit to state
            self.app._update_packages.append(final_record.model_dump())
            self._resolvePackageStorageState()
            self.app.updatePackagesChanged.emit()
            self.app._set_status(f"Added skill package: {final_record.name}")
            capture_event(
                "skill_package_added", {"source_type": final_record.source_type}
            )
        except Exception as e:
            logger.error("Failed to add skill package: %s", e)
            self.app._set_status(f"Error adding skill package: {e}")

    @Slot(int, dict)
    def updateUpdatePackage(self, index: int, data: dict):
        """Updates configuration for an existing skill package."""
        if 0 <= index < len(self.app._update_packages):
            try:
                # Preserve internal state
                is_updating = self.app._update_packages[index].get("is_updating", False)

                from skill_manager.core.skill_packages import (
                    check_skill_package_versions,
                    normalize_skill_package_config,
                )

                normalized = normalize_skill_package_config(data)
                record = UpdatePackageRecord.model_validate(normalized)
                record.is_updating = is_updating

                # Refresh versions
                checked_data = check_skill_package_versions(record.model_dump())
                final_record = UpdatePackageRecord.model_validate(checked_data)

                self.app._update_packages[index] = final_record.model_dump()
                self._resolvePackageStorageState()
                self.app.updatePackagesChanged.emit()
                self.app._set_status(f"Updated skill package: {final_record.name}")
            except Exception as e:
                logger.error("Failed to update skill package: %s", e)
                self.app._set_status(f"Error updating skill package: {e}")

    @Slot(int)
    def removeUpdatePackage(self, index: int):
        """Removes a skill package."""
        if 0 <= index < len(self.app._update_packages):
            source = self.app._update_packages.pop(index)
            self._resolvePackageStorageState()
            self.app.updatePackagesChanged.emit()
            self.app._set_status(f"Removed update package: {source.get('name')}")
            capture_event(
                "skill_package_removed", {"source_type": source.get("source_type", "unknown")}
            )

    @Slot(int)
    def runPackageUpdate(self, index: int):
        """Runs update for a single skill package."""
        if 0 <= index < len(self.app._update_packages):
            self._resolvePackageStorageState()
            source = self.app._update_packages[index]
            source["is_updating"] = True
            source["just_finished"] = False
            self.app.updatePackagesChanged.emit()
            self.app._set_status(f"Updating {source.get('name')}...")

            def run():
                from datetime import datetime
                from pathlib import Path

                from skill_manager.core.persistence import (
                    load_package_skill_inventory,
                    save_package_skill_inventory,
                )
                from skill_manager.core.skill_packages import (
                    diff_package_inventory,
                    inventory_removals_verified,
                    package_project_path_conflicts,
                    promote_package_storage,
                    run_skill_package_update,
                    scan_package_inventory,
                )

                try:
                    pkg_path = (
                        source.get("resolved_package_path")
                        or source.get("package_path")
                        or source.get("local_path")
                    )
                    if not pkg_path and self.app._sources:
                        potential_path = self.app._sources[0]
                        if Path(potential_path).resolve() == Path.cwd().resolve():
                            source["package_path"] = str(
                                Path(potential_path) / ".agents" / "skills"
                            )
                        else:
                            source["package_path"] = potential_path
                    else:
                        source["package_path"] = pkg_path

                    conflicts = package_project_path_conflicts([source], self.app._projects)
                    if conflicts:
                        conflict_path = conflicts[0]
                        raise RuntimeError(
                            f"Package storage path overlaps a project skills path: {conflict_path}"
                        )

                    def log_callback(msg):
                        QTimer.singleShot(0, self.app, lambda: self.app._set_status(msg))

                    inventory = load_package_skill_inventory()
                    previous_inventory = inventory.get(source.get("package_id"), {})
                    if source.get("storage_mode") == "grouped":
                        promote_result = promote_package_storage(source, previous_inventory)
                        if promote_result.get("skipped"):
                            raise RuntimeError(
                                f"Could not promote package storage for {source.get('name')}"
                            )

                    updated_source = {**source, **run_skill_package_update(source, log_callback)}
                    current_inventory = scan_package_inventory(updated_source)
                    inventory_diff = diff_package_inventory(previous_inventory, current_inventory)
                    removals_verified = inventory_removals_verified(
                        previous_inventory, current_inventory
                    )
                    if current_inventory.get("scan_ok"):
                        inventory[updated_source["package_id"]] = current_inventory
                    updated_source["managed_folders"] = sorted(
                        current_inventory.get("skills", {}).keys()
                    )
                    updated_source["removed_folders"] = (
                        inventory_diff["removed"] if removals_verified else []
                    )
                    updated_source["updated_folders"] = sorted(
                        set(inventory_diff["added"]) | set(inventory_diff["updated"])
                    )
                    updated_source["removals_verified"] = removals_verified
                    save_package_skill_inventory(inventory)
                    source.update(updated_source)
                    source["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M")
                    capture_event(
                        "skill_package_updated",
                        {"source_type": source.get("source_type", "unknown"), "success": True},
                    )
                except Exception as e:
                    capture_event(
                        "skill_package_updated",
                        {"source_type": source.get("source_type", "unknown"), "success": False},
                    )
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

                        removed = source.get("removed_folders", [])
                        removals_verified = source.get("removals_verified", False)
                        if removed and removals_verified:
                            self.app._library_model.removeSkillsByPath(removed)
                            self.app._quick_copy_model.removeSkillsByPath(removed)

                        updated = source.get("updated_folders", [])
                        if updated:
                            from skill_manager.core.discovery import DiscoveryService
                            from skill_manager.core.persistence import patch_cache_add

                            pkg_path = (
                                source.get("resolved_package_path")
                                or source.get("package_path")
                                or source.get("local_path")
                                or ""
                            )
                            service = DiscoveryService(
                                sources=[pkg_path] if pkg_path else [],
                                projects=[],
                                archive_paths=self.app._archive_paths,
                                starred_paths=self.app._starred_paths,
                                project_aliases=self.app._project_aliases,
                            )
                            discovered = []
                            for folder in updated:
                                try:
                                    folder_path = Path(pkg_path) / folder if pkg_path else Path(folder)
                                    if folder_path.is_dir():
                                        skill_data = service.discover_single_skill(
                                            folder_path, folder_path
                                        )
                                        if skill_data:
                                            discovered.append(skill_data)
                                except Exception:
                                    pass

                            if discovered:
                                patch_cache_add(discovered)
                                self._merge_discovered_skills(discovered)

                        self.config.set("skills", self.app._update_packages)

                    QTimer.singleShot(0, self.app, finalize_ui)

            self.app.task_runner.run(run)

    @Slot(str)
    def syncProject(self, path: str):
        """Synchronizes and updates all skills in a specific project."""
        if path not in self.app._projects:
            return

        self.app._set_status(f"Updating {self.app.getProjectLabel(path)}...")
        if path not in self.app._syncing_projects:
            self.app._syncing_projects.append(path)
            self.app.projectsChanged.emit()

        def run_sync():
            try:
                from skill_manager.core.discovery import DiscoveryService
                from skill_manager.core.parsing import (
                    build_skill_search_text,
                    categorize_skill,
                    parse_skill_md,
                )
                from skill_manager.core.persistence import patch_cache_add
                from skill_manager.core.quick_copy import discover_package_skills

                source_skills = discover_package_skills(
                    sources=self.app._sources,
                    parse_skill_md=parse_skill_md,
                    categorize_skill=categorize_skill,
                    build_search_text=build_skill_search_text,
                )

                from skill_manager.core.copier import copy_skill_folders_to_projects

                result = copy_skill_folders_to_projects(source_skills, [path], update_only=True)

                discovered_skills = []
                if result["details"]:
                    service = DiscoveryService(
                        sources=list(self.app._sources),
                        projects=self.app._projects,
                        archive_paths=self.app._archive_paths,
                        starred_paths=self.app._starred_paths,
                        project_aliases=self.app._project_aliases,
                    )
                    for detail in result["details"]:
                        if detail["status"] in ("copied", "merged") and detail.get("message"):
                            skill_path = Path(detail["message"])
                            proj_path = Path(detail["project"])
                            try:
                                skill_data = service.discover_single_skill(skill_path, proj_path)
                                if skill_data:
                                    discovered_skills.append(skill_data)
                            except Exception as exc:
                                logger.error(
                                    "[SYNC SCAN] Failed scanning %s: %s", skill_path, exc
                                )

                if discovered_skills:
                    patch_cache_add(discovered_skills)

                    def update_ui():
                        self._merge_discovered_skills(discovered_skills)

                    QTimer.singleShot(0, self.app, update_ui)

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

    @Slot()
    def updateAllOutdated(self):
        """Updates all skills that are marked as outdated."""
        # This was missing in the restored version, let's add it.
        self.app._set_status("Updating all outdated skills...")
        # Placeholder for implementation if needed, or call updateNow
        self.updateNow()

    @Slot(int)
    def clearPackageJustFinished(self, index: int):
        if 0 <= index < len(self.app._update_packages):
            self.app._update_packages[index]["just_finished"] = False
            self.app.updatePackagesChanged.emit()
