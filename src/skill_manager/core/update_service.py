"""
Update service for handling background skill updates and project syncing.
"""

from collections.abc import Callable
from pathlib import Path
from typing import Any
import logging

logger = logging.getLogger(__name__)

from skill_manager.core.copier import copy_skill_folders_to_projects
from skill_manager.core.parsing import build_skill_search_text, categorize_skill, parse_skill_md
from skill_manager.core.persistence import (
    load_package_skill_inventory,
    load_project_skill_ownership,
    save_package_skill_inventory,
    save_project_skill_ownership,
)
from skill_manager.core.quick_copy import (
    delete_project_skill_folders,
    discover_package_skills,
    discover_project_skills,
)
from skill_manager.core.skill_packages import (
    check_skill_package_versions,
    diff_package_inventory,
    inventory_removals_verified,
    normalize_skill_package_config,
    package_project_path_conflicts,
    promote_package_storage,
    resolve_package_storage,
    run_skill_package_update,
    scan_package_inventory,
)
from skill_manager.core.skill_packages.process import sanitize_token
from skill_manager.utils.task_runner import BackgroundTaskRunner, TaskRunner


def _log_update(level: str, event: str, **fields: Any) -> None:
    details = " ".join(
        f"{key}={sanitize_token(str(value))}"
        for key, value in fields.items()
        if value not in (None, "")
    )
    msg = f"{event}{(' ' + details) if details else ''}"
    if level.upper() == "ERROR":
        logger.error(msg)
    elif level.upper() == "WARN":
        logger.warning(msg)
    elif level.upper() == "DEBUG":
        logger.debug(msg)
    else:
        logger.info(msg)


class UpdateService:
    def __init__(
        self,
        sources: list[str],
        projects: list[str],
        update_packages: list[dict[str, Any]] = None,
        project_aliases: dict[str, str] = None,
        update_sources: list[dict[str, Any]] = None,
        task_runner: TaskRunner = None,
    ):
        self.sources = sources
        self.projects = projects
        self.update_packages = (
            update_packages if update_packages is not None else (update_sources or [])
        )
        self.update_packages = [
            normalize_skill_package_config(package) for package in self.update_packages
        ]
        self.project_aliases = project_aliases or {}
        self.task_runner = task_runner or BackgroundTaskRunner()

    def run_global_update(
        self,
        status_callback: Callable[[str], None],
        source_progress_callback: Callable[[int, dict[str, Any]], None],
        completion_callback: Callable[[dict[str, Any], list[dict[str, Any]]], None],
    ) -> None:
        """Runs a full global update: packages first, then projects."""

        self.task_runner.run(
            self.run_global_update_sync,
            args=(status_callback, source_progress_callback, completion_callback),
        )

    def run_global_update_sync(
        self,
        status_callback: Callable[[str], None],
        source_progress_callback: Callable[[int, dict[str, Any]], None],
        completion_callback: Callable[[dict[str, Any], list[dict[str, Any]]], None],
    ) -> None:
        try:
            status_callback("Phase 1/2: Updating skill packages...")
            removed_by_package = []
            updated_skill_folders = set()
            package_id_by_folder = {}
            inventory = load_package_skill_inventory()
            self.update_packages = resolve_package_storage(self.update_packages, inventory)
            conflicts = package_project_path_conflicts(self.update_packages, self.projects)
            unsafe_project_keys = {self._ownership_project_key(path) for path in conflicts}
            if conflicts:
                for conflict in conflicts:
                    _log_update(
                        "WARN",
                        "update.path_conflict",
                        path=conflict,
                        action="skip_project_cleanup_sync",
                    )
                status_callback(
                    "Skipped project cleanup/sync for package paths that overlap project skills."
                )
            package_id_by_source = self._package_id_by_source_path()

            for index, source in enumerate(self.update_packages):
                try:
                    source_path = (
                        source.get("resolved_package_path")
                        or source.get("package_path")
                        or source.get("local_path")
                    )
                    if source_path and self._ownership_project_key(source_path) in unsafe_project_keys:
                        _log_update(
                            "WARN",
                            "update.package.skipped",
                            name=source.get("name"),
                            path=source_path,
                            reason="path_conflict",
                        )
                        source["is_updating"] = False
                        source["just_finished"] = False
                        source_progress_callback(index, source)
                        self.update_packages[index] = source
                        continue

                    _log_update(
                        "INFO",
                        "update.package.start",
                        name=source.get("name"),
                        path=source_path,
                    )
                    # Fallback for local_path if not set on the source
                    if not source.get("local_path") and self.sources:
                        # Safety: ensure we don't accidentally relocate to the project root
                        import os
                        from pathlib import Path

                        potential_path = self.sources[0]
                        try:
                            # Use resolve() to handle relative paths like '.'
                            resolved_potential = Path(os.path.expanduser(potential_path)).resolve()
                            if resolved_potential == Path.cwd().resolve():
                                source["local_path"] = str(
                                    resolved_potential / ".agents" / "skills"
                                )
                            else:
                                source["local_path"] = str(resolved_potential)
                        except Exception:
                            source["local_path"] = potential_path

                    previous_inventory = inventory.get(source.get("package_id"), {})
                    if source.get("storage_mode") == "grouped":
                        promote_result = promote_package_storage(source, previous_inventory)
                        if promote_result.get("skipped"):
                            raise RuntimeError(
                                f"Could not promote package storage for {source.get('name')}"
                            )

                    updated_source = {**source, **run_skill_package_update(source, status_callback)}
                    updated_source["is_updating"] = False
                    updated_source["just_finished"] = True

                    current_inventory = scan_package_inventory(updated_source)
                    inventory_diff = diff_package_inventory(previous_inventory, current_inventory)
                    removals_verified = inventory_removals_verified(
                        previous_inventory, current_inventory
                    )
                    if current_inventory.get("scan_ok"):
                        inventory[updated_source["package_id"]] = current_inventory
                    elif previous_inventory:
                        status_callback(
                            "Skipped package inventory save for "
                            f"{updated_source.get('name')}: {current_inventory.get('scan_error')}"
                        )
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

                    # Track which folders were actually updated/relocated
                    folders_changed = updated_source.get("updated_folders") or []
                    if folders_changed:
                        updated_skill_folders.update(folders_changed)
                        for folder_name in folders_changed:
                            package_id_by_folder[folder_name] = updated_source.get("package_id")

                    if updated_source.get("removed_folders"):
                        for folder_name in updated_source["removed_folders"]:
                            removed_by_package.append(
                                {
                                    "folder_name": folder_name,
                                    "package_id": updated_source.get("package_id"),
                                    "removal_verified": True,
                                }
                            )
                    elif inventory_diff["removed"] and not removals_verified:
                        status_callback(
                            "Skipped project deletion for "
                            f"{updated_source.get('name')}: package inventory scan was unsafe"
                        )
                    source_progress_callback(index, updated_source)
                    self.update_packages[index] = updated_source
                    package_id_by_source.update(self._package_id_by_source_path([updated_source]))
                    _log_update(
                        "INFO",
                        "update.package.done",
                        name=updated_source.get("name"),
                        updated=len(updated_source.get("updated_folders") or []),
                        removed=len(updated_source.get("removed_folders") or []),
                    )
                except Exception as exc:
                    _log_update(
                        "ERROR",
                        "update.package.failed",
                        name=source.get("name"),
                        error=exc,
                    )
                    source["is_updating"] = False
                    source_progress_callback(index, source)

            save_package_skill_inventory(inventory)

            # Phase 2/2: Syncing to projects
            status_callback("Phase 2/2: Updating project folders...")
            safe_projects = self._safe_projects_for_update(unsafe_project_keys)
            self._cleanup_removed_project_skills(
                removed_by_package, status_callback, projects=safe_projects
            )

            # Discover all skills from packages using the correct package discovery method
            source_skills = discover_package_skills(
                sources=self._package_discovery_sources(),
                parse_skill_md=parse_skill_md,
                categorize_skill=categorize_skill,
                build_search_text=build_skill_search_text,
            )

            all_raw_skills = []
            for skill in source_skills:
                # Only sync if this skill was actually updated in Phase 1
                # This prevents the "copying all skills" frustration
                if not updated_skill_folders or skill.get("folder_name") in updated_skill_folders:
                    package_id = package_id_by_folder.get(
                        skill.get("folder_name")
                    ) or package_id_by_source.get(
                        self._ownership_project_key(skill.get("source_path", ""))
                    )
                    if package_id:
                        skill = {**skill, "package_id": package_id}
                    all_raw_skills.append(skill)

            if all_raw_skills and safe_projects:
                status_callback(f"Syncing {len(all_raw_skills)} updated skills to projects...")
                result = copy_skill_folders_to_projects(
                    all_raw_skills, safe_projects, update_only=True
                )
                self._record_project_skill_ownership(all_raw_skills, result)
            elif all_raw_skills:
                status_callback("Skipped project sync: no safe project folders to update.")
                _log_update(
                    "WARN",
                    "update.sync.skipped",
                    reason="no_safe_projects",
                    skills=len(all_raw_skills),
                )
                result = {"copied": 0, "merged": 0, "skipped": 0, "failed": 0, "details": []}
            else:
                status_callback("No skills needed syncing to projects.")
                result = {"copied": 0, "merged": 0, "skipped": 0, "failed": 0, "details": []}

            completion_callback(result, self.update_packages)
        except Exception as exc:
            import traceback

            traceback.print_exc()
            status_callback(f"Global update failed: {exc}")

    def _cleanup_removed_project_skills(
        self,
        removed_folders: list[Any],
        status_callback: Callable[[str], None],
        projects: list[str] | None = None,
    ) -> None:
        if not removed_folders:
            return

        status_callback(f"Cleaning up {len(removed_folders)} removed skills from projects...")
        _log_update("INFO", "update.cleanup.removed", count=len(removed_folders))
        ownership = load_project_skill_ownership()
        projects_state = discover_project_skills(
            projects=projects if projects is not None else self.projects,
            parse_skill_md=parse_skill_md,
            categorize_skill=categorize_skill,
            build_search_text=build_skill_search_text,
            project_aliases=self.project_aliases,
        )
        removed_map = {}
        for item in removed_folders:
            if isinstance(item, dict):
                folder_name = item.get("folder_name")
                if folder_name and item.get("removal_verified") is True:
                    removed_map[folder_name] = item.get("package_id")
            elif item:
                removed_map[str(item)] = None

        blocked_project_keys = self._package_storage_keys()
        skills_to_delete = [
            skill
            for project in projects_state
            for skill in project.get("skills", [])
            if self._ownership_project_key(skill.get("project_path", ""))
            not in blocked_project_keys
            and self._is_removed_skill_owned_by_package(
                skill, removed_map.get(skill.get("folder_name")), ownership
            )
        ]

        if skills_to_delete:
            delete_project_skill_folders(skills_to_delete)
            self._remove_project_skill_ownership(skills_to_delete, ownership)
        else:
            _log_update("INFO", "update.cleanup.deleted", count=0)

    @staticmethod
    def _ownership_project_key(project_path: str) -> str:
        return str(Path(project_path).resolve()).casefold()

    def _package_discovery_sources(self):
        sources = list(self.sources)
        seen = {self._ownership_project_key(path) for path in sources if path}
        for package in self.update_packages:
            package_path = package.get("package_path") or package.get("local_path")
            if not package_path:
                continue
            key = self._ownership_project_key(package_path)
            if key not in seen:
                sources.append(package_path)
                seen.add(key)
        return sources

    def _safe_projects_for_update(self, unsafe_project_keys: set[str]) -> list[str]:
        if not unsafe_project_keys:
            return list(self.projects)

        from skill_manager.core.copier import normalize_project_skills_path

        safe_projects = []
        for project in self.projects:
            project_path, error = normalize_project_skills_path(project)
            candidate = project if error else project_path
            if self._ownership_project_key(candidate) in unsafe_project_keys:
                _log_update(
                    "WARN",
                    "update.project.skipped",
                    project=candidate,
                    reason="path_conflict",
                )
                continue
            safe_projects.append(project)
        return safe_projects

    def _package_id_by_source_path(self, packages=None):
        package_map = {}
        for package in packages or self.update_packages:
            package_id = package.get("package_id")
            package_path = package.get("package_path") or package.get("local_path")
            if package_id and package_path:
                package_map[self._ownership_project_key(package_path)] = package_id
        return package_map

    def _package_storage_keys(self):
        keys = {self._ownership_project_key(path) for path in self.sources if path}
        for package in self.update_packages:
            package_path = package.get("resolved_package_path") or package.get("package_path")
            if package_path:
                keys.add(self._ownership_project_key(package_path))
        return keys

    @classmethod
    def _is_removed_skill_owned_by_package(cls, skill, package_id, ownership):
        folder_name = skill.get("folder_name")
        project_key = cls._ownership_project_key(skill.get("project_path", ""))
        if not folder_name or folder_name not in ownership.get(project_key, {}):
            return False
        if not package_id:
            return False
        return ownership[project_key].get(folder_name) == package_id

    @classmethod
    def _remove_project_skill_ownership(cls, skills, ownership):
        for skill in skills:
            project_key = cls._ownership_project_key(skill.get("project_path", ""))
            folder_name = skill.get("folder_name")
            if project_key in ownership and folder_name:
                ownership[project_key].pop(folder_name, None)
                if not ownership[project_key]:
                    ownership.pop(project_key, None)
        save_project_skill_ownership(ownership)

    @classmethod
    def _record_project_skill_ownership(cls, source_skills, copy_result):
        package_by_folder = {
            skill.get("folder_name"): skill.get("package_id")
            for skill in source_skills
            if skill.get("folder_name") and skill.get("package_id")
        }
        if not package_by_folder:
            return

        ownership = load_project_skill_ownership()
        changed = False
        for detail in copy_result.get("details", []):
            if detail.get("status") not in {"copied", "merged"}:
                continue
            destination = Path(detail.get("message", ""))
            folder_name = destination.name
            package_id = package_by_folder.get(folder_name)
            if not package_id:
                continue
            project_key = cls._ownership_project_key(str(destination.parent))
            ownership.setdefault(project_key, {})[folder_name] = package_id
            changed = True

        if changed:
            save_project_skill_ownership(ownership)

    def scan_for_updates(
        self,
        status_callback: Callable[[str], None],
        completion_callback: Callable[[list[dict[str, Any]], list[dict[str, Any]]], None],
    ) -> None:
        """Scans for version updates and compares skills across projects."""

        self.task_runner.run(
            self.scan_for_updates_sync,
            args=(status_callback, completion_callback),
        )

    def scan_for_updates_sync(
        self,
        status_callback: Callable[[str], None],
        completion_callback: Callable[[list[dict[str, Any]], list[dict[str, Any]]], None],
    ) -> None:
        try:
            status_callback("Scanning for updates...")
            source_skills = discover_package_skills(
                sources=self._package_discovery_sources(),
                parse_skill_md=parse_skill_md,
                categorize_skill=categorize_skill,
                build_search_text=build_skill_search_text,
            )
            projects_state = discover_project_skills(
                projects=self.projects,
                parse_skill_md=parse_skill_md,
                categorize_skill=categorize_skill,
                build_search_text=build_skill_search_text,
                project_aliases=self.project_aliases,
            )

            updated_sources = []
            for source in self.update_packages:
                try:
                    updated_sources.append(check_skill_package_versions(source))
                except Exception as exc:
                    logger.error(f"[ERROR] Failed to check versions for {source.get('name')}: {exc}")
                    updated_sources.append(source)

            completion_callback(
                self.compare_source_and_project_skills(source_skills, projects_state),
                updated_sources,
            )
        except Exception as exc:
            import traceback

            traceback.print_exc()
            status_callback(f"Scan failed: {exc}")

    @staticmethod
    def compare_source_and_project_skills(
        source_skills: list[dict[str, Any]],
        projects_state: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        source_map = {skill["folder_name"]: skill for skill in source_skills}
        project_skill_maps = [
            {
                "project_label": project["project_label"],
                "skills_map": {skill["folder_name"]: skill for skill in project["skills"]},
            }
            for project in projects_state
        ]

        results = []
        for folder_name, source_skill in source_map.items():
            item_projects = []
            item_status = "up_to_date"
            for project_map in project_skill_maps:
                if folder_name in project_map["skills_map"]:
                    item_projects.append(
                        {"name": project_map["project_label"], "status": "up_to_date"}
                    )
                else:
                    item_status = "missing"
                    item_projects.append(
                        {"name": project_map["project_label"], "status": "missing"}
                    )

            results.append(
                {
                    "name": source_skill["name"],
                    "folder_name": folder_name,
                    "status": item_status,
                    "status_text": item_status.replace("_", " ").title(),
                    "projects": item_projects,
                }
            )
        return results
