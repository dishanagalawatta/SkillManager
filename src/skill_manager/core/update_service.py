"""
Update service for handling background skill updates and project syncing.
"""
import threading
from collections.abc import Callable
from typing import Any

from skill_manager.core.copier import copy_skill_folders_to_targets
from skill_manager.core.parsing import build_skill_search_text, categorize_skill, parse_skill_md
from skill_manager.core.quick_copy import (
    delete_project_skill_folders,
    discover_project_skills,
    discover_source_skills,
)
from skill_manager.core.skill_sources import check_skill_source_versions, run_skill_source_update


class UpdateService:
    def __init__(self, sources: list[str], targets: list[str], update_sources: list[dict[str, Any]], target_aliases: dict[str, str] = None):
        self.sources = sources
        self.targets = targets
        self.update_sources = update_sources
        self.target_aliases = target_aliases or {}

    def run_global_update(self,
                          status_callback: Callable[[str], None],
                          source_progress_callback: Callable[[int, dict[str, Any]], None],
                          completion_callback: Callable[[dict[str, Any], list[dict[str, Any]]], None]) -> None:
        """Runs a full global update: sources first, then projects."""

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
            status_callback("Phase 1/2: Updating skill sources...")
            all_removed_folders = []

            for index, source in enumerate(self.update_sources):
                try:
                    updated_source = run_skill_source_update(source, status_callback)
                    updated_source["is_updating"] = False
                    updated_source["just_finished"] = True
                    if updated_source.get("removed_folders"):
                        all_removed_folders.extend(updated_source["removed_folders"])
                    source_progress_callback(index, updated_source)
                except Exception as exc:
                    print(f"[UPDATE] Source failed: {source.get('name')} - {exc}")
                    source["is_updating"] = False
                    source_progress_callback(index, source)

            status_callback("Phase 2/2: Updating project folders...")
            self._cleanup_removed_project_skills(all_removed_folders, status_callback)

            projects = discover_project_skills(
                targets=self.sources,
                parse_skill_md=parse_skill_md,
                categorize_skill=categorize_skill,
                build_search_text=build_skill_search_text,
            )
            all_raw_skills = [skill for project in projects for skill in project.get("skills", [])]
            result = copy_skill_folders_to_targets(all_raw_skills, self.targets, update_only=True)
            completion_callback(result, self.update_sources)
        except Exception as exc:
            import traceback
            traceback.print_exc()
            status_callback(f"Global update failed: {exc}")

    def _cleanup_removed_project_skills(
        self,
        removed_folders: list[str],
        status_callback: Callable[[str], None],
    ) -> None:
        if not removed_folders:
            return

        status_callback(f"Cleaning up {len(removed_folders)} removed skills from projects...")
        target_projects_state = discover_project_skills(
            targets=self.targets,
            parse_skill_md=parse_skill_md,
            categorize_skill=categorize_skill,
            build_search_text=build_skill_search_text,
            target_aliases=self.target_aliases,
        )
        removed_set = set(removed_folders)
        skills_to_delete = [
            skill
            for project in target_projects_state
            for skill in project.get("skills", [])
            if skill.get("folder_name") in removed_set
        ]

        if skills_to_delete:
            delete_project_skill_folders(skills_to_delete)

    def scan_for_updates(self,
                         status_callback: Callable[[str], None],
                         completion_callback: Callable[[list[dict[str, Any]], list[dict[str, Any]]], None]) -> None:
        """Scans for version updates and compares skills across targets."""

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
            source_skills = discover_source_skills(
                sources=self.sources,
                parse_skill_md=parse_skill_md,
                categorize_skill=categorize_skill,
                build_search_text=build_skill_search_text,
            )
            target_projects = discover_project_skills(
                targets=self.targets,
                parse_skill_md=parse_skill_md,
                categorize_skill=categorize_skill,
                build_search_text=build_skill_search_text,
                target_aliases=self.target_aliases,
            )

            updated_sources = []
            for source in self.update_sources:
                try:
                    updated_sources.append(check_skill_source_versions(source))
                except Exception as exc:
                    print(f"[ERROR] Failed to check versions for {source.get('name')}: {exc}")
                    updated_sources.append(source)

            completion_callback(
                self.compare_source_and_target_skills(source_skills, target_projects),
                updated_sources,
            )
        except Exception as exc:
            import traceback
            traceback.print_exc()
            status_callback(f"Scan failed: {exc}")

    @staticmethod
    def compare_source_and_target_skills(
        source_skills: list[dict[str, Any]],
        target_projects: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        source_map = {skill["folder_name"]: skill for skill in source_skills}
        target_skill_maps = [
            {
                "project_label": project["project_label"],
                "skills_map": {skill["folder_name"]: skill for skill in project["skills"]},
            }
            for project in target_projects
        ]

        results = []
        for folder_name, source_skill in source_map.items():
            item_targets = []
            item_status = "up_to_date"
            for target_map in target_skill_maps:
                if folder_name in target_map["skills_map"]:
                    item_targets.append({"name": target_map["project_label"], "status": "up_to_date"})
                else:
                    item_status = "missing"
                    item_targets.append({"name": target_map["project_label"], "status": "missing"})

            results.append({
                "name": source_skill["name"],
                "folder_name": folder_name,
                "status": item_status,
                "status_text": item_status.replace("_", " ").title(),
                "targets": item_targets,
            })
        return results
