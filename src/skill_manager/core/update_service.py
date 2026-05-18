"""
Update service for handling background skill updates and project syncing.
"""

import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any

from skill_manager.core.copier import copy_skill_folders_to_projects
from skill_manager.core.parsing import build_skill_search_text, categorize_skill, parse_skill_md
from skill_manager.core.persistence import (
    load_project_skill_ownership,
    save_project_skill_ownership,
)
from skill_manager.core.quick_copy import (
    delete_project_skill_folders,
    discover_package_skills,
    discover_project_skills,
)
from skill_manager.core.skill_packages import check_skill_package_versions, run_skill_package_update


class UpdateService:
    def __init__(
        self,
        sources: list[str],
        projects: list[str],
        update_packages: list[dict[str, Any]] = None,
        project_aliases: dict[str, str] = None,
        update_sources: list[dict[str, Any]] = None,
    ):
        self.sources = sources
        self.projects = projects
        self.update_packages = (
            update_packages if update_packages is not None else (update_sources or [])
        )
        self.project_aliases = project_aliases or {}

    def run_global_update(
        self,
        status_callback: Callable[[str], None],
        source_progress_callback: Callable[[int, dict[str, Any]], None],
        completion_callback: Callable[[dict[str, Any], list[dict[str, Any]]], None],
    ) -> None:
        """Runs a full global update: packages first, then projects."""

        threading.Thread(
            target=self.run_global_update_sync,
            args=(status_callback, source_progress_callback, completion_callback),
            daemon=True,
        ).start()

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
            package_id_by_source = self._package_id_by_source_path()

            for index, source in enumerate(self.update_packages):
                try:
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

                    updated_source = run_skill_package_update(source, status_callback)
                    updated_source["is_updating"] = False
                    updated_source["just_finished"] = True

                    # Track which folders were actually updated/relocated
                    if updated_source.get("managed_folders"):
                        updated_skill_folders.update(updated_source["managed_folders"])
                        for folder_name in updated_source["managed_folders"]:
                            package_id_by_folder[folder_name] = updated_source.get("package_id")

                    if updated_source.get("removed_folders"):
                        for folder_name in updated_source["removed_folders"]:
                            removed_by_package.append(
                                {
                                    "folder_name": folder_name,
                                    "package_id": updated_source.get("package_id"),
                                }
                            )
                    source_progress_callback(index, updated_source)
                    package_id_by_source.update(self._package_id_by_source_path([updated_source]))
                except Exception as exc:
                    print(f"[UPDATE] Package failed: {source.get('name')} - {exc}")
                    source["is_updating"] = False
                    source_progress_callback(index, source)

            # Phase 2/2: Syncing to projects
            status_callback("Phase 2/2: Updating project folders...")
            self._cleanup_removed_project_skills(removed_by_package, status_callback)

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

            if all_raw_skills:
                status_callback(f"Syncing {len(all_raw_skills)} updated skills to projects...")
                result = copy_skill_folders_to_projects(
                    all_raw_skills, self.projects, update_only=True
                )
                self._record_project_skill_ownership(all_raw_skills, result)
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
    ) -> None:
        if not removed_folders:
            return

        status_callback(f"Cleaning up {len(removed_folders)} removed skills from projects...")
        ownership = load_project_skill_ownership()
        projects_state = discover_project_skills(
            projects=self.projects,
            parse_skill_md=parse_skill_md,
            categorize_skill=categorize_skill,
            build_search_text=build_skill_search_text,
            project_aliases=self.project_aliases,
        )
        removed_map = {}
        for item in removed_folders:
            if isinstance(item, dict):
                folder_name = item.get("folder_name")
                if folder_name:
                    removed_map[folder_name] = item.get("package_id")
            elif item:
                removed_map[str(item)] = None

        skills_to_delete = [
            skill
            for project in projects_state
            for skill in project.get("skills", [])
            if self._is_removed_skill_owned_by_package(
                skill, removed_map.get(skill.get("folder_name")), ownership
            )
        ]

        if skills_to_delete:
            delete_project_skill_folders(skills_to_delete)
            self._remove_project_skill_ownership(skills_to_delete, ownership)

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

    def _package_id_by_source_path(self, packages=None):
        package_map = {}
        for package in packages or self.update_packages:
            package_id = package.get("package_id")
            package_path = package.get("package_path") or package.get("local_path")
            if package_id and package_path:
                package_map[self._ownership_project_key(package_path)] = package_id
        return package_map

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

        threading.Thread(
            target=self.scan_for_updates_sync,
            args=(status_callback, completion_callback),
            daemon=True,
        ).start()

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
                    print(f"[ERROR] Failed to check versions for {source.get('name')}: {exc}")
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
