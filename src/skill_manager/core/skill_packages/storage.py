import hashlib
import logging
import os
import re
import shutil
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def normalize_storage_key(path: str | Path) -> str:
    return str(Path(os.path.expanduser(str(path))).resolve()).casefold()


def safe_package_folder_name(package: dict[str, Any]) -> str:
    name = str(package.get("name") or package.get("package_name") or "package").strip()
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", name).strip(".-").lower() or "package"
    package_id = str(package.get("package_id") or "")
    suffix = package_id[-8:] if package_id else hashlib.sha1(slug.encode("utf-8")).hexdigest()[:8]
    if suffix.lower() not in slug.lower():
        return f"{slug}-{suffix}"
    return slug


def resolve_package_storage(
    packages: list[dict[str, Any]],
    inventory: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Assigns each package an isolated final storage path."""
    inventory = inventory or {}
    final_keys: set[str] = set()
    result = []

    for package in packages:
        item = dict(package)
        configured = (
            item.get("configured_package_path")
            or item.get("package_path")
            or item.get("local_path")
            or ""
        )
        configured = str(configured).strip()
        item["configured_package_path"] = configured

        if not configured:
            result.append(item)
            continue

        configured_path = Path(os.path.expanduser(configured)).resolve()
        package_id = item.get("package_id")
        prior = inventory.get(package_id, {}) if package_id else {}
        old_resolved = item.get("resolved_package_path") or item.get("package_path")

        child_name = safe_package_folder_name(item)

        # Always group unless configured path explicitly matches the package slug or name
        if (
            configured_path.name.lower() == child_name.lower()
            or configured_path.name.lower() == str(item.get("name") or "").lower()
        ):
            resolved = configured_path
        else:
            resolved = configured_path / child_name

        # Prevent collisions
        counter = 2
        original_resolved = resolved
        while normalize_storage_key(resolved) in final_keys:
            resolved = original_resolved.parent / f"{original_resolved.name}-{counter}"
            counter += 1

        if resolved == configured_path:
            item["storage_mode"] = "direct"
        else:
            item["storage_mode"] = "grouped"

        item["resolved_package_path"] = str(resolved)
        item["package_path"] = str(resolved)
        item["local_path"] = str(resolved)
        item["_previous_resolved_package_path"] = str(
            prior.get("resolved_package_path") or old_resolved or ""
        )
        final_keys.add(normalize_storage_key(resolved))
        result.append(item)

    return result


def package_project_path_conflicts(
    packages: list[dict[str, Any]], projects: list[str]
) -> list[str]:
    from skill_manager.core.copier import normalize_project_skills_path

    project_keys = set()
    for project in projects:
        if not project:
            continue
        project_path, error = normalize_project_skills_path(project)
        if error:
            project_path = project
        project_keys.add(normalize_storage_key(project_path))

    conflicts = []
    for package in packages:
        package_path = package.get("resolved_package_path") or package.get("package_path")
        if package_path and normalize_storage_key(package_path) in project_keys:
            conflicts.append(str(package_path))
    return conflicts


def scan_package_inventory(package: dict[str, Any]) -> dict[str, Any]:
    package_path = Path(
        os.path.expanduser(
            str(package.get("resolved_package_path") or package.get("package_path") or "")
        )
    )
    skills: dict[str, dict[str, Any]] = {}
    scan_ok = True
    scan_error = ""
    path_exists = package_path.is_dir()
    if path_exists:
        try:
            children = sorted(package_path.iterdir(), key=lambda item: item.name.lower())
        except OSError as exc:
            children = []
            scan_ok = False
            scan_error = str(exc)
        for child in children:
            skill_md = child / "SKILL.md"
            if not child.is_dir() or not skill_md.is_file():
                continue
            stat = skill_md.stat()
            skills[child.name] = {
                "folder_name": child.name,
                "local_path": str(child.resolve()),
                "skill_md_path": str(skill_md.resolve()),
                "fingerprint": skill_fingerprint(child),
                "mtime": stat.st_mtime,
            }
    else:
        scan_ok = False
        scan_error = f"Package path does not exist: {package_path}"

    return {
        "package_id": package.get("package_id"),
        "configured_package_path": package.get("configured_package_path") or "",
        "resolved_package_path": str(package_path.resolve()),
        "storage_mode": package.get("storage_mode") or "direct",
        "path_exists": path_exists,
        "scan_ok": scan_ok,
        "scan_error": scan_error,
        "skill_count": len(skills),
        "skills": skills,
    }


def diff_package_inventory(previous: dict[str, Any] | None, current: dict[str, Any]):
    previous_skills = (previous or {}).get("skills", {}) if isinstance(previous, dict) else {}
    current_skills = current.get("skills", {})
    previous_names = set(previous_skills)
    current_names = set(current_skills)
    added = sorted(current_names - previous_names)
    removed = sorted(previous_names - current_names)
    updated = sorted(
        name
        for name in previous_names & current_names
        if previous_skills[name].get("fingerprint") != current_skills[name].get("fingerprint")
    )
    unchanged = sorted((previous_names & current_names) - set(updated))
    return {"added": added, "updated": updated, "removed": removed, "unchanged": unchanged}


def inventory_removals_verified(previous: dict[str, Any] | None, current: dict[str, Any]) -> bool:
    previous_skills = (previous or {}).get("skills", {}) if isinstance(previous, dict) else {}
    if not current.get("scan_ok"):
        return False
    return not (previous_skills and not current.get("skills"))


def promote_package_storage(package: dict[str, Any], previous_inventory: dict[str, Any] | None):
    old_path = Path(os.path.expanduser(str(package.get("_previous_resolved_package_path") or "")))
    new_path = Path(os.path.expanduser(str(package.get("resolved_package_path") or "")))
    if (
        not old_path
        or not new_path
        or normalize_storage_key(old_path) == normalize_storage_key(new_path)
    ):
        return {"moved": 0, "skipped": 0}
    if not old_path.is_dir():
        return {"moved": 0, "skipped": 0}
    if new_path.exists() and any(new_path.iterdir()):
        return {"moved": 0, "skipped": 1}

    skill_names = set((previous_inventory or {}).get("skills", {}))
    if not skill_names:
        return {"moved": 0, "skipped": 0}

    moved = 0
    new_path.mkdir(parents=True, exist_ok=True)
    for folder_name in sorted(skill_names):
        source = old_path / folder_name
        if not source.is_dir() or not (source / "SKILL.md").is_file():
            continue
        destination = new_path / folder_name
        if destination.exists():
            return {"moved": moved, "skipped": 1}
        shutil.move(str(source), str(destination))
        moved += 1

    return {"moved": moved, "skipped": 0}


def skill_fingerprint(path: Path) -> str:
    """Fast fingerprint using file metadata (mtime, size, name)."""
    parts = []
    try:
        files = sorted(p for p in path.rglob("*") if p.is_file())
    except OSError:
        files = []
    for file_path in files:
        try:
            stat = file_path.stat()
            rel = file_path.relative_to(path).as_posix()
            parts.append(f"{rel}:{stat.st_mtime}:{stat.st_size}")
        except OSError:
            continue
    return hashlib.sha1("\n".join(parts).encode("utf-8")).hexdigest()
