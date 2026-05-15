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

        def run_full_sync():
            try:
                # Phase 1: Update skill sources
                status_callback("Phase 1/2: Updating skill sources...")
                all_removed_folders = []

                for i in range(len(self.update_sources)):
                    source = self.update_sources[i]
                    try:
                        # run_skill_source_update handles version detection and returns updated source
                        updated_source = run_skill_source_update(source, status_callback)
                        updated_source["is_updating"] = False
                        updated_source["just_finished"] = True

                        # Collect removed folders for project-wide cleanup
                        if updated_source.get("removed_folders"):
                            all_removed_folders.extend(updated_source["removed_folders"])

                        # Report progress
                        source_progress_callback(i, updated_source)
                    except Exception as e:
                        print(f"[UPDATE] Source failed: {source.get('name')} - {e}")
                        source["is_updating"] = False
                        source_progress_callback(i, source)

                # Phase 2: Update project folders
                status_callback("Phase 2/2: Updating project folders...")

                # Cleanup removed folders from targets first
                if all_removed_folders:
                    status_callback(f"Cleaning up {len(all_removed_folders)} removed skills from projects...")
                    target_projects_state = discover_project_skills(
                        targets=self.targets,
                        parse_skill_md=parse_skill_md,
                        categorize_skill=categorize_skill,
                        build_search_text=build_skill_search_text,
                        target_aliases=self.target_aliases
                    )
                    removed_set = set(all_removed_folders)
                    skills_to_delete = []
                    for p in target_projects_state:
                        for s in p.get("skills", []):
                            if s.get("folder_name") in removed_set:
                                skills_to_delete.append(s)

                    if skills_to_delete:
                        delete_project_skill_folders(skills_to_delete)

                # Discover new source skills to sync
                projects = discover_project_skills(
                    targets=self.sources,
                    parse_skill_md=parse_skill_md,
                    categorize_skill=categorize_skill,
                    build_search_text=build_skill_search_text
                )

                all_raw_skills = []
                for p in projects:
                    all_raw_skills.extend(p.get("skills", []))

                result = copy_skill_folders_to_targets(all_raw_skills, self.targets, update_only=True)

                completion_callback(result, self.update_sources)

            except Exception as e:
                import traceback
                traceback.print_exc()
                status_callback(f"Global update failed: {e}")

        threading.Thread(target=run_full_sync, daemon=True).start()

    def scan_for_updates(self,
                         status_callback: Callable[[str], None],
                         completion_callback: Callable[[list[dict[str, Any]], list[dict[str, Any]]], None]) -> None:
        """Scans for version updates and compares skills across targets."""

        def run_scan():
            try:
                status_callback("Scanning for updates...")
                # 1. Discover skills in sources
                source_skills = discover_source_skills(
                    sources=self.sources,
                    parse_skill_md=parse_skill_md,
                    categorize_skill=categorize_skill,
                    build_search_text=build_skill_search_text,
                )

                # 2. Discover skills in targets
                target_projects = discover_project_skills(
                    targets=self.targets,
                    parse_skill_md=parse_skill_md,
                    categorize_skill=categorize_skill,
                    build_search_text=build_skill_search_text,
                    target_aliases=self.target_aliases
                )

                # 3. Check versions
                updated_sources = []
                for source in self.update_sources:
                    try:
                        updated_sources.append(check_skill_source_versions(source))
                    except Exception as e:
                        print(f"[ERROR] Failed to check versions for {source.get('name')}: {e}")
                        updated_sources.append(source)

                # 4. Compare skills
                results = []
                source_map = {s["folder_name"]: s for s in source_skills}
                target_skill_maps = []
                for p in target_projects:
                    target_skill_maps.append({
                        "project_label": p["project_label"],
                        "skills_map": {s["folder_name"]: s for s in p["skills"]}
                    })

                for folder_name, source_skill in source_map.items():
                    item_targets = []
                    item_status = "up_to_date"

                    for tm in target_skill_maps:
                        target_skill = tm["skills_map"].get(folder_name)
                        if target_skill:
                            item_targets.append({"name": tm["project_label"], "status": "up_to_date"})
                        else:
                            item_status = "missing"
                            item_targets.append({"name": tm["project_label"], "status": "missing"})

                    results.append({
                        "name": source_skill["name"],
                        "folder_name": folder_name,
                        "status": item_status,
                        "status_text": item_status.replace("_", " ").title(),
                        "targets": item_targets
                    })

                completion_callback(results, updated_sources)
            except Exception as e:
                import traceback
                traceback.print_exc()
                status_callback(f"Scan failed: {e}")

        threading.Thread(target=run_scan, daemon=True).start()
