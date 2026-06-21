"""Copy skills between source and project directories.

Handles path normalization, skill package validation, and batch copy operations.
Includes diagnostic logging for all path resolution decisions.
"""

from __future__ import annotations

import logging
import os
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)


def copy_skill_folders_to_projects(skills, projects, update_only=False):
    result = {"copied": 0, "merged": 0, "skipped": 0, "failed": 0, "details": []}

    normalized_projects = [_normalize_project_path(project) for project in projects]

    for skill in skills:
        source_path, folder_name, error = _normalize_skill_package(skill)
        if error or source_path is None:
            result["skipped"] += max(1, len(normalized_projects))
            result["details"].append(
                {
                    "skill": skill.get("name") or skill.get("folder_name") or "Unknown",
                    "project": "",
                    "status": "skipped",
                    "message": error or "Skill source path unavailable.",
                }
            )
            continue

        for project_path, project_error in normalized_projects:
            skill_label = skill.get("name") or folder_name
            if project_error:
                result["skipped"] += 1
                result["details"].append(
                    {
                        "skill": skill_label,
                        "project": str(project_path),
                        "status": "skipped",
                        "message": project_error,
                    }
                )
                continue

            destination_path = project_path / folder_name
            existed = destination_path.exists()

            if update_only and not existed:
                # Skip skills that don't already exist in the project when update_only is True
                continue

            try:
                project_path.mkdir(parents=True, exist_ok=True)
                shutil.copytree(source_path, destination_path, dirs_exist_ok=True)
            except Exception as exc:
                result["failed"] += 1
                result["details"].append(
                    {
                        "skill": skill_label,
                        "project": str(project_path),
                        "status": "failed",
                        "message": str(exc),
                    }
                )
                continue

            if existed:
                result["merged"] += 1
                status = "merged"
            else:
                result["copied"] += 1
                status = "copied"
            result["details"].append(
                {
                    "skill": skill_label,
                    "project": str(project_path),
                    "status": status,
                    "message": str(destination_path),
                }
            )

    logger.info(
        "skill_copy_batch: copied=%d merged=%d skipped=%d failed=%d",
        result["copied"],
        result["merged"],
        result["skipped"],
        result["failed"],
    )
    return result


def normalize_project_skills_path(project):
    path, error = _normalize_project_path(project)
    return str(path), error


def get_skills_dir(project_path: str | Path) -> Path:
    """Return the skills directory for a project, regardless of input shape.

    Handles all normalization cases:
    - Path already at <root>/.agents/skills → return as-is
    - Path already at <root>/skills → return as-is
    - Path at project root → return <root>/.agents/skills (existing or intended)
    - Path at .agents → return <path>/skills

    This is the single source of truth for resolving skills directory from a stored
    project path. Use this instead of hardcoding ``Path(project_path) / ".agents" / "skills"``.
    """
    path = Path(project_path).resolve()
    name_lower = path.name.lower()

    # Already at skills level
    if name_lower == "skills":
        return path

    # Already at .agents level
    if name_lower == ".agents":
        return path / "skills"

    # Already at .agents/skills level
    if name_lower == "skills" and path.parent.name.lower() == ".agents":
        return path

    # Project root — check for .agents/skills
    potential = path / ".agents" / "skills"
    if potential.exists() and potential.is_dir():
        return potential

    # Project root — .agents/skills doesn't exist yet, return intended path
    return potential


def get_commands_dir(project_path: str | Path) -> Path:
    """Return the commands directory for a project, regardless of input shape.

    Mirrors ``get_skills_dir`` but for ``.agents/commands/``.
    """
    from skill_manager.core.quick_copy import project_root_for_project

    root = project_root_for_project(Path(project_path))
    return root / ".agents" / "commands"


def copy_command_files_to_projects(commands: list[dict], projects: list) -> dict:
    """Copy command .md files from source to each project's .agents/commands/ dir.

    Skips (does not overwrite) when the destination file already exists.
    Returns ``{copied, skipped, failed, details}``.
    """
    result = {"copied": 0, "skipped": 0, "failed": 0, "details": []}

    normalized_projects = [_normalize_project_path(project) for project in projects]

    for cmd in commands:
        raw_path = cmd.get("local_path") or ""
        source_file = Path(os.path.expanduser(raw_path)).resolve()
        cmd_name = cmd.get("name") or source_file.name

        if not source_file.is_file():
            result["failed"] += 1
            result["details"].append(
                {
                    "skill": cmd_name,
                    "project": "",
                    "status": "failed",
                    "message": f"Command file does not exist: {source_file}",
                }
            )
            continue

        for project_path, project_error in normalized_projects:
            if project_error:
                result["skipped"] += 1
                result["details"].append(
                    {
                        "skill": cmd_name,
                        "project": str(project_path),
                        "status": "skipped",
                        "message": project_error,
                    }
                )
                continue

            commands_dir = get_commands_dir(project_path)
            dest = commands_dir / source_file.name

            if dest.exists():
                result["skipped"] += 1
                result["details"].append(
                    {
                        "skill": cmd_name,
                        "project": str(project_path),
                        "status": "skipped",
                        "message": f"Command already exists: {dest}",
                    }
                )
                continue

            try:
                commands_dir.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source_file, dest)
            except Exception as exc:
                result["failed"] += 1
                result["details"].append(
                    {
                        "skill": cmd_name,
                        "project": str(project_path),
                        "status": "failed",
                        "message": str(exc),
                    }
                )
                continue

            result["copied"] += 1
            result["details"].append(
                {
                    "skill": cmd_name,
                    "project": str(project_path),
                    "status": "copied",
                    "message": str(dest),
                }
            )

    logger.info(
        "command_copy_batch: copied=%d skipped=%d failed=%d",
        result["copied"],
        result["skipped"],
        result["failed"],
    )
    return result


def _normalize_skill_package(skill):
    raw_path = skill.get("local_path") or ""
    if not raw_path:
        return None, "", "Skill has no local folder path."

    source_path = Path(os.path.expanduser(raw_path)).resolve()
    if not source_path.is_dir():
        return None, "", f"Skill folder does not exist: {source_path}"
    if not (source_path / "SKILL.md").is_file():
        return None, "", f"Skill folder is missing SKILL.md: {source_path}"

    folder_name = str(skill.get("folder_name") or source_path.name).strip()
    folder_name = folder_name.replace("\\", "/").strip("/").split("/")[-1]
    if not folder_name:
        return None, "", "Skill folder name is empty."

    return source_path, folder_name, ""


def _normalize_project_path(project):
    raw_path = str(project or "").strip()
    if not raw_path:
        return Path("."), "Project path is empty."

    project_path = Path(os.path.expanduser(raw_path)).resolve()

    if project_path.exists() and not project_path.is_dir():
        error_msg = f"Project directory is not a folder: {project_path}"
        logger.info(
            "project_path_normalized: raw=%s name=%s error=%s",
            raw_path,
            project_path.name,
            error_msg,
        )
        return project_path, error_msg

    # Auto-detect .agents/skills if project root was provided
    found = False
    if project_path.name.lower() not in ("skills", ".agents"):
        potential = project_path / ".agents" / "skills"
        if potential.exists() and potential.is_dir():
            project_path = potential.resolve()
            found = True

        logger.info(
            "project_path_normalized: raw=%s name=%s potential_skills_dir=%s "
            "found_potential=%s normalized=%s exists=%s",
            raw_path,
            Path(raw_path).name,
            str(potential),
            found,
            str(project_path),
            project_path.exists(),
        )

        if not found:
            # Assume it's a project root, use the standard .agents/skills
            project_path = (project_path / ".agents" / "skills").resolve()
    else:
        logger.info(
            "project_path_normalized: raw=%s name=%s (already skills/agents) "
            "normalized=%s exists=%s",
            raw_path,
            project_path.name,
            str(project_path),
            project_path.exists(),
        )

    if not project_path.exists():
        # Validate that the intended project root exists
        if project_path.name == "skills" and project_path.parent.name == ".agents":
            project_root = project_path.parent.parent
            if not project_root.is_dir():
                error_msg = f"Project root folder does not exist: {project_root}"
                logger.warning(
                    "project_path_normalized: raw=%s root_missing=%s",
                    raw_path,
                    str(project_root),
                )
                return project_path, error_msg
        elif not project_path.parent.is_dir():
            error_msg = f"Project parent folder does not exist: {project_path.parent}"
            logger.warning(
                "project_path_normalized: raw=%s parent_missing=%s",
                raw_path,
                str(project_path.parent),
            )
            return project_path, error_msg

    return project_path, ""
