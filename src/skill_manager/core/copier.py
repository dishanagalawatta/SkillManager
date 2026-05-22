import os
import shutil
from pathlib import Path


def copy_skill_folders_to_projects(skills, projects, update_only=False):
    result = {"copied": 0, "merged": 0, "skipped": 0, "failed": 0, "details": []}

    normalized_projects = [_normalize_project_path(project) for project in projects]

    for skill in skills:
        source_path, folder_name, error = _normalize_skill_package(skill)
        if error:
            result["skipped"] += max(1, len(normalized_projects))
            result["details"].append(
                {
                    "skill": skill.get("name") or skill.get("folder_name") or "Unknown",
                    "project": "",
                    "status": "skipped",
                    "message": error,
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

    return result


def normalize_project_skills_path(project):
    path, error = _normalize_project_path(project)
    return str(path), error


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
        return project_path, f"Project directory is not a folder: {project_path}"

    # Auto-detect .agents/skills if project root was provided
    if project_path.name.lower() not in ("skills", ".agents"):
        found = False
        potential = project_path / ".agents" / "skills"
        if potential.exists() and potential.is_dir():
            project_path = potential.resolve()
            found = True
        if not found:
            # Assume it's a project root, use the standard .agents/skills
            project_path = (project_path / ".agents" / "skills").resolve()

    if not project_path.exists():
        # Validate that the intended project root exists
        if project_path.name == "skills" and project_path.parent.name == ".agents":
            project_root = project_path.parent.parent
            if not project_root.is_dir():
                return project_path, f"Project root folder does not exist: {project_root}"
        elif not project_path.parent.is_dir():
            return project_path, f"Project parent folder does not exist: {project_path.parent}"

    return project_path, ""
