import os
import shutil
from pathlib import Path


def copy_skill_folders_to_targets(skills, targets):
    result = {
        "copied": 0,
        "merged": 0,
        "skipped": 0,
        "failed": 0,
        "details": []
    }

    normalized_targets = [_normalize_target_path(target) for target in targets]

    for skill in skills:
        source_path, folder_name, error = _normalize_skill_source(skill)
        if error:
            result["skipped"] += max(1, len(normalized_targets))
            result["details"].append({
                "skill": skill.get("name") or skill.get("folder_name") or "Unknown",
                "target": "",
                "status": "skipped",
                "message": error
            })
            continue

        for target_path, target_error in normalized_targets:
            skill_label = skill.get("name") or folder_name
            if target_error:
                result["skipped"] += 1
                result["details"].append({
                    "skill": skill_label,
                    "target": str(target_path),
                    "status": "skipped",
                    "message": target_error
                })
                continue

            destination_path = target_path / folder_name
            existed = destination_path.exists()
            try:
                target_path.mkdir(parents=False, exist_ok=True)
                shutil.copytree(source_path, destination_path, dirs_exist_ok=True)
            except Exception as exc:
                result["failed"] += 1
                result["details"].append({
                    "skill": skill_label,
                    "target": str(target_path),
                    "status": "failed",
                    "message": str(exc)
                })
                continue

            if existed:
                result["merged"] += 1
                status = "merged"
            else:
                result["copied"] += 1
                status = "copied"
            result["details"].append({
                "skill": skill_label,
                "target": str(target_path),
                "status": status,
                "message": str(destination_path)
            })

    return result


def _normalize_skill_source(skill):
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


def _normalize_target_path(target):
    raw_path = str(target or "").strip()
    if not raw_path:
        return Path("."), "Target path is empty."

    target_path = Path(os.path.expanduser(raw_path)).resolve()
    if target_path.exists() and not target_path.is_dir():
        return target_path, f"Target is not a folder: {target_path}"
    if not target_path.exists() and not target_path.parent.is_dir():
        return target_path, f"Target parent folder does not exist: {target_path.parent}"

    return target_path, ""
