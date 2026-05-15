"""
Discovery service for finding and processing skills from sources and targets.
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
from skill_manager.core.quick_copy import discover_project_skills, discover_source_skills


class DiscoveryService:
    def __init__(self, sources: list[str], targets: list[str], archive_paths: list[str], essential_paths: list[str], target_aliases: dict[str, str] = None):
        self.sources = sources
        self.targets = targets
        self.archive_paths = archive_paths
        self.essential_paths = essential_paths
        self.target_aliases = target_aliases or {}

    def discover_all(self, use_cache: bool = True, cache_callback: Callable[[dict[str, Any]], None] = None) -> dict[str, Any]:
        """Performs full discovery of skills from all sources and targets."""

        # 1. Try cache first
        if use_cache:
            cached_data = load_cache()
            if cached_data and cache_callback:
                cache_callback(cached_data)

        # 2a. Discover from master sources
        source_skills_raw = discover_source_skills(
            sources=self.sources,
            parse_skill_md=parse_skill_md,
            categorize_skill=categorize_skill,
            build_search_text=build_skill_search_text,
        )

        all_skills = []
        for skill in source_skills_raw:
            all_skills.append(self._transform_skill(skill, is_source=True))

        # 2b. Discover from project targets
        projects = discover_project_skills(
            targets=self.targets,
            parse_skill_md=parse_skill_md,
            categorize_skill=categorize_skill,
            build_search_text=build_skill_search_text,
            target_aliases=self.target_aliases
        )

        for p in projects:
            for skill in p.get("skills", []):
                all_skills.append(self._transform_skill(skill, is_source=False, project_label=p.get("project_label")))

            # Also discover commands in manuals/ subdir
            target_path = Path(p["target_path"])
            manuals_dir = target_path / "manuals"
            if manuals_dir.is_dir():
                for cmd_file in manuals_dir.glob("*.md"):
                    cmd_data = self._process_command_file(cmd_file, p)
                    if cmd_data:
                        all_skills.append(cmd_data)

        # 3. Pre-compute metadata
        cats = sorted({s["category"] for s in all_skills if s["category"]})
        proj_labels = sorted({p["project_label"] for p in projects})

        result = {
            "skills": all_skills,
            "projects": projects,
            "categories": cats,
            "project_labels": proj_labels,
            "status": f"Found {len(all_skills)} skills in master library ({len(projects)} project targets)"
        }

        # 4. Update cache
        save_cache(result)

        return result

    def _transform_skill(self, skill: dict[str, Any], is_source: bool, project_label: str = None) -> dict[str, Any]:
        """Normalizes raw skill data into the format expected by the UI models."""
        metadata = skill.get("metadata", {})
        local_path = skill.get("local_path", "")

        data = {
            "id": str(local_path),
            "name": skill.get("name", "Unknown"),
            "category": skill.get("category", "Uncategorized"),
            "description": skill.get("description", ""),
            "local_path": local_path,
            "project_label": skill.get("project_label") or project_label or ("Master Library" if is_source else "Unknown Project"),
            "project_root": skill.get("project_root", ""),
            "target_path": skill.get("target_path", ""),
            "is_essential": metadata.get("essential", False) or local_path in self.essential_paths,
            "is_bundle": skill.get("is_bundle", False),
            "manuals": skill.get("manuals", []),
            "is_selected": False,
            "is_archived": local_path in self.archive_paths,
            "search_text": skill.get("search_text", ""),
            "raw_content": skill.get("raw_content", ""),
            "body_content": skill.get("body_content", ""),
            "risk": metadata.get("risk", "Unknown"),
            "source": metadata.get("source", "Unknown"),
            "date": str(metadata.get("date_added") or metadata.get("date", "Unknown")),
            "is_source": is_source,
        }

        if not is_source:
            data.update({
                "skill_base_relative": skill.get("skill_base_relative", ""),
                "folder_name": skill.get("folder_name", ""),
                "skill_md_path": skill.get("skill_md_path", "")
            })

        return data

    def _process_command_file(self, cmd_file: Path, project: dict[str, Any]) -> dict[str, Any] | None:
        """Parses a command markdown file and returns its normalized representation."""
        cmd_data_raw = parse_command_md(str(cmd_file))
        if not cmd_data_raw:
            return None

        data = {
            "id": str(cmd_file),
            "name": cmd_data_raw.get("name") or cmd_file.stem,
            "category": cmd_data_raw.get("category") or "Custom Commands",
            "description": cmd_data_raw.get("description", ""),
            "local_path": str(cmd_file),
            "project_label": project.get("project_label", "Unknown Project"),
            "project_root": project.get("project_root", ""),
            "target_path": project.get("target_path", ""),
            "is_essential": False,
            "is_bundle": False,
            "manuals": [],
            "is_selected": False,
            "is_archived": False,
            "raw_content": cmd_data_raw.get("raw_content", ""),
            "body_content": cmd_data_raw.get("body_content", ""),
            "risk": "Low",
            "source": "Custom",
            "date": str(cmd_data_raw.get("metadata", {}).get("date", "Unknown")),
            "is_source": False,
            "is_command": True,
            "client": cmd_data_raw.get("client", "")
        }
        data["search_text"] = build_skill_search_text(data)
        return data
