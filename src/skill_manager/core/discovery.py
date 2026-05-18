"""
Discovery service for finding and processing skills from sources and projects.
"""

from collections.abc import Callable
from pathlib import Path
from typing import Any

from skill_manager.core.parsing import (
    build_skill_search_text,
    categorize_skill,
    parse_command_md,
    parse_skill_md,
)
from skill_manager.core.persistence import load_cache, save_cache
from skill_manager.core.quick_copy import discover_package_skills, discover_project_skills


class DiscoveryService:
    def __init__(
        self,
        sources: list[str],
        projects: list[str],
        archive_paths: list[str],
        starred_paths: list[str],
        project_aliases: dict[str, str] = None,
    ):
        self.sources = sources
        self.projects = projects
        self.archive_paths = archive_paths
        self.starred_paths = starred_paths
        self.project_aliases = project_aliases or {}

    def discover_all(
        self, use_cache: bool = True, cache_callback: Callable[[dict[str, Any]], None] = None
    ) -> dict[str, Any]:
        """Performs full discovery of skills from all sources and projects."""

        # 1. Try cache first
        if use_cache:
            try:
                cached_data = load_cache()
                if cached_data and cache_callback:
                    cache_callback(cached_data)
            except Exception as e:
                print(f"[DISCOVERY] Error loading cache: {e}")

        # 2a. Discover from master packages
        package_skills_raw = discover_package_skills(
            sources=self.sources,
            parse_skill_md=parse_skill_md,
            categorize_skill=categorize_skill,
            build_search_text=build_skill_search_text,
        )

        all_skills = []
        for skill in package_skills_raw:
            all_skills.append(self.transform_skill(skill, is_package=True))

        # 2b. Discover from project skill folders
        projects_state = discover_project_skills(
            projects=self.projects,
            parse_skill_md=parse_skill_md,
            categorize_skill=categorize_skill,
            build_search_text=build_skill_search_text,
            project_aliases=self.project_aliases,
        )

        for p in projects_state:
            for skill in p.get("skills", []):
                all_skills.append(
                    self.transform_skill(
                        skill, is_package=False, project_label=p.get("project_label")
                    )
                )

            # Also discover commands in commands/ subdir
            project_path = Path(p["project_path"])
            commands_dir = project_path / "commands"
            if commands_dir.is_dir():
                for cmd_file in commands_dir.glob("*.md"):
                    cmd_data = self._process_command_file(cmd_file, p)
                    if cmd_data:
                        all_skills.append(cmd_data)

        # 3. Pre-compute metadata
        cats = sorted({s["category"] for s in all_skills if s["category"]})
        proj_labels = sorted({p["project_label"] for p in projects_state})

        result = {
            "skills": all_skills,
            "projects": projects_state,
            "categories": cats,
            "project_labels": proj_labels,
            "status": f"Found {len(all_skills)} skills in master library ({len(projects_state)} projects)",
        }

        # 4. Update cache
        save_cache(result)

        return result

    def transform_skill(
        self, skill: dict[str, Any], is_package: bool, project_label: str = None
    ) -> dict[str, Any]:
        """Normalizes raw skill data into the format expected by the UI models."""
        metadata = skill.get("metadata", {})
        local_path = skill.get("local_path", "")

        data = {
            "id": str(local_path),
            "name": skill.get("name", "Unknown"),
            "main_category": skill.get("main_category", "⚙️ System & Workflow"),
            "category": skill.get("category", "Uncategorized"),
            "description": skill.get("description", ""),
            "local_path": local_path,
            "project_label": skill.get("project_label")
            or project_label
            or ("Master Library" if is_package else "Unknown Project"),
            "project_root": skill.get("project_root", ""),
            "project_path": skill.get("project_path", ""),
            "is_starred": metadata.get("starred", False)
            or metadata.get("essential", False)
            or local_path in self.starred_paths,
            "is_bundle": skill.get("is_bundle", False),
            "commands": skill.get("commands", []),
            "is_selected": False,
            "is_archived": local_path in self.archive_paths,
            "search_text": skill.get("search_text", ""),
            "raw_content": skill.get("raw_content", ""),
            "body_content": skill.get("body_content", ""),
            "risk": metadata.get("risk", "Unknown"),
            "source": metadata.get("source", "Unknown"),
            "date": str(metadata.get("date_added") or metadata.get("date", "Unknown")),
            "is_package": is_package,
            "is_source": is_package,  # Compatibility
        }

        if not is_package:
            data.update(
                {
                    "skill_base_relative": skill.get("skill_base_relative", ""),
                    "folder_name": skill.get("folder_name", ""),
                    "skill_md_path": skill.get("skill_md_path", ""),
                }
            )

        return data


    def _process_command_file(
        self, cmd_file: Path, project: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Parses a command markdown file and returns its normalized representation."""
        cmd_data_raw = parse_command_md(str(cmd_file))
        if not cmd_data_raw:
            return None

        data = {
            "id": str(cmd_file),
            "name": cmd_data_raw.get("name") or cmd_file.stem,
            "main_category": cmd_data_raw.get("main_category") or "⚙️ System & Workflow",
            "category": cmd_data_raw.get("category") or "Custom Commands",
            "description": cmd_data_raw.get("description", ""),
            "local_path": str(cmd_file),
            "project_label": project.get("project_label", "Unknown Project"),
            "project_root": project.get("project_root", ""),
            "project_path": project.get("project_path", ""),
            "is_starred": False,
            "is_bundle": False,
            "commands": [],
            "is_selected": False,
            "is_archived": False,
            "raw_content": cmd_data_raw.get("raw_content", ""),
            "body_content": cmd_data_raw.get("body_content", ""),
            "risk": "Low",
            "source": "Custom",
            "date": str(cmd_data_raw.get("metadata", {}).get("date", "Unknown")),
            "is_package": False,
            "is_source": False,  # Compatibility
            "is_command": True,
            "client": cmd_data_raw.get("client", ""),
        }
        data["search_text"] = build_skill_search_text(data)
        return data

    def discover_single_skill(self, skill_path: Path, project_path: Path) -> dict[str, Any] | None:
        """Parses and normalizes a single skill at skill_path belonging to project_path."""
        import os

        from skill_manager.core.parsing import (
            build_skill_search_text,
            categorize_skill,
            parse_skill_md,
        )
        from skill_manager.core.quick_copy import (
            _classification_text,
            _project_root_for_project,
            _resolve_resilient_path,
            _skill_base_relative,
            project_label,
        )

        skill_md_path = skill_path / "SKILL.md"
        if not skill_md_path.is_file():
            return None

        resolved_project = _resolve_resilient_path(project_path)
        if not resolved_project:
            return None
        project_key = os.path.normcase(str(resolved_project))

        skill_data = parse_skill_md(str(skill_md_path))
        if not skill_data.get("name"):
            skill_data["name"] = skill_path.name
        skill_data["folder_name"] = skill_path.name
        skill_data["local_path"] = str(skill_path)
        skill_data["skill_md_path"] = str(skill_md_path)
        skill_data["project_key"] = project_key
        skill_data["project_path"] = str(resolved_project)
        skill_data["project_root"] = str(_project_root_for_project(resolved_project))
        skill_data["skill_base_relative"] = _skill_base_relative(resolved_project)
        skill_data["project_label"] = project_label(
            resolved_project, self.project_aliases, str(project_path)
        )
        skill_data.setdefault("metadata", {})
        cat_info = categorize_skill(
            skill_data.get("name", ""),
            _classification_text(skill_data),
        )
        skill_data["main_category"] = cat_info.get("main_category", "")
        skill_data["category"] = cat_info.get("sub_category", "")
        skill_data["search_text"] = build_skill_search_text(skill_data)

        # Now transform it using public transform_skill
        return self.transform_skill(skill_data, is_package=False, project_label=skill_data["project_label"])

