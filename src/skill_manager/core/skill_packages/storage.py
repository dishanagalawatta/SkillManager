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
        from skill_manager.core.copier import repair_malformed_path

        configured = repair_malformed_path(configured)
        item["configured_package_path"] = configured

        if not configured:
            result.append(item)
            continue

        configured_path = Path(os.path.expanduser(configured)).resolve()
        package_id = item.get("package_id")
        prior = inventory.get(package_id, {}) if package_id else {}
        old_resolved = item.get("resolved_package_path") or item.get("package_path")
        if old_resolved:
            old_resolved = repair_malformed_path(str(old_resolved))

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


def _on_rmtree_error(func, path, _exc_info):
    """Error handler for shutil.rmtree to clear read-only permissions on Windows."""
    import stat

    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except Exception:
        pass


def is_safe_deletion_target(
    target_path: Path,
    protected_paths: list[str | Path] | None = None,
) -> bool:
    """Checks whether target_path is safe to delete.

    A path is unsafe if it is:
    - Root ('/', 'C:\\', etc.)
    - User home directory
    - Current working directory
    - The DATA_DIR root itself
    - Any path in protected_paths or an ancestor of any path in protected_paths.
    """
    try:
        resolved_target = target_path.expanduser().resolve()
    except Exception:
        return False

    # Root / anchor
    if resolved_target == Path(resolved_target.anchor) or str(resolved_target) in ("/", "\\"):
        return False

    # User home
    try:
        if resolved_target == Path.home().resolve():
            return False
    except Exception:
        pass

    # Current working dir
    try:
        if resolved_target == Path.cwd().resolve():
            return False
    except Exception:
        pass

    # DATA_DIR root
    from skill_manager.core.config import DATA_DIR

    try:
        if resolved_target == DATA_DIR.resolve():
            return False
    except Exception:
        pass

    # Protected paths (projects, source roots)
    if protected_paths:
        for p in protected_paths:
            if not p:
                continue
            try:
                resolved_p = Path(os.path.expanduser(str(p))).resolve()
                if resolved_target == resolved_p:
                    return False
                # If target is ancestor of a protected path, unsafe!
                if resolved_p.is_relative_to(resolved_target):
                    return False
            except Exception:
                continue

    return True


def delete_package_storage(
    package: dict[str, Any],
    protected_paths: list[str | Path] | None = None,
) -> dict[str, Any]:
    """Safely cleans up all filesystem artifacts for a deleted package.

    Removes:
    1. The package storage folder (if grouped or dedicated directory).
    2. Any managed subfolders if direct mode is inside a shared directory.
    3. The git clone directory under package_clones.
    4. Associated manifest and lock files in the target root.

    Returns a dict with:
    - 'deleted_folders': list[str] of successfully deleted directory paths
    - 'deleted_files': list[str] of successfully deleted file paths
    - 'deleted_skill_paths': list[str] of all skill paths removed
    - 'errors': list[str] of any deletion errors encountered
    """
    deleted_folders: list[str] = []
    deleted_files: list[str] = []
    deleted_skill_paths: list[str] = []
    errors: list[str] = []

    from skill_manager.core.config import DATA_DIR

    package_name = safe_package_folder_name(package)
    configured_pkg_path = str(package.get("configured_package_path") or "").strip()
    resolved_pkg_path = str(
        package.get("resolved_package_path")
        or package.get("package_path")
        or package.get("local_path")
        or ""
    ).strip()
    storage_mode = package.get("storage_mode") or "direct"
    managed_folders = list(package.get("managed_folders") or [])
    clone_path = str(package.get("clone_path") or "").strip()
    name_prefix = str(package.get("name") or "").strip()

    # 1. Package Storage Directory / Managed Folders
    if resolved_pkg_path:
        dest_base = Path(os.path.expanduser(resolved_pkg_path))
        if dest_base.is_dir():
            # If storage_mode is grouped or if dest_base is not the configured root path
            # and is safe to delete:
            is_grouped = storage_mode == "grouped"
            if not is_grouped and configured_pkg_path:
                conf_base = Path(os.path.expanduser(configured_pkg_path)).resolve()
                if dest_base.resolve() != conf_base:
                    is_grouped = True

            # Also consider dedicated if folder name matches package slug
            if not is_grouped:
                folder_name_lower = dest_base.name.lower()
                if (
                    folder_name_lower == package_name.lower()
                    or folder_name_lower == name_prefix.lower()
                ):
                    is_grouped = True

            if is_grouped and is_safe_deletion_target(dest_base, protected_paths):
                # Collect skill paths inside before deleting
                try:
                    for child in dest_base.iterdir():
                        if child.is_dir():
                            deleted_skill_paths.append(str(child.resolve()))
                except Exception:
                    pass

                try:
                    shutil.rmtree(dest_base, onerror=_on_rmtree_error)
                    deleted_folders.append(str(dest_base.resolve()))
                    logger.info("[PACKAGE_CLEANUP] Deleted package folder: %s", dest_base)
                except Exception as exc:
                    err = f"Failed to delete package folder {dest_base}: {exc}"
                    logger.error("[PACKAGE_CLEANUP] %s", err)
                    errors.append(err)
            else:
                # Direct mode or shared root: delete managed folders only
                for folder_name in managed_folders:
                    child_folder = dest_base / folder_name
                    if child_folder.is_dir() and is_safe_deletion_target(
                        child_folder, protected_paths
                    ):
                        deleted_skill_paths.append(str(child_folder.resolve()))
                        try:
                            shutil.rmtree(child_folder, onerror=_on_rmtree_error)
                            deleted_folders.append(str(child_folder.resolve()))
                            logger.info(
                                "[PACKAGE_CLEANUP] Deleted managed skill folder: %s", child_folder
                            )
                        except Exception as exc:
                            err = f"Failed to delete managed folder {child_folder}: {exc}"
                            logger.error("[PACKAGE_CLEANUP] %s", err)
                            errors.append(err)

    # 2. Git Clone Directory
    candidate_clones = []
    if clone_path:
        candidate_clones.append(Path(os.path.expanduser(clone_path)))
    if package_name:
        candidate_clones.append(DATA_DIR / "package_clones" / package_name)

    for clone_dir in candidate_clones:
        if clone_dir.is_dir() and is_safe_deletion_target(clone_dir, protected_paths):
            try:
                resolved_clone = clone_dir.resolve()
                if resolved_clone.is_dir() and str(resolved_clone) not in deleted_folders:
                    shutil.rmtree(resolved_clone, onerror=_on_rmtree_error)
                    deleted_folders.append(str(resolved_clone))
                    logger.info("[PACKAGE_CLEANUP] Deleted package clone: %s", resolved_clone)
            except Exception as exc:
                err = f"Failed to delete clone directory {clone_dir}: {exc}"
                logger.error("[PACKAGE_CLEANUP] %s", err)
                errors.append(err)

    # 3. Lockfiles and Manifests
    target_root = None
    if resolved_pkg_path:
        target_root = Path(os.path.expanduser(resolved_pkg_path)).parent
    if not target_root or target_root.resolve() == Path.cwd().resolve():
        target_root = DATA_DIR

    prefixes = [p for p in (name_prefix, package_name) if p]
    for prefix in prefixes:
        for lock_template in (
            f".{prefix}-skill-lock.json",
            f"{prefix}-skills-lock.json",
            f".{prefix}-antigravity-install-manifest.json",
        ):
            lock_path = target_root / lock_template
            if lock_path.is_file() and is_safe_deletion_target(lock_path, protected_paths):
                try:
                    lock_path.unlink()
                    deleted_files.append(str(lock_path.resolve()))
                    logger.info(
                        "[PACKAGE_CLEANUP] Deleted package manifest/lockfile: %s", lock_path
                    )
                except Exception as exc:
                    err = f"Failed to delete lockfile {lock_path}: {exc}"
                    logger.error("[PACKAGE_CLEANUP] %s", err)
                    errors.append(err)

    return {
        "deleted_folders": deleted_folders,
        "deleted_files": deleted_files,
        "deleted_skill_paths": deleted_skill_paths,
        "errors": errors,
    }


def skill_fingerprint(path: Path) -> str:
    """Fast fingerprint using file metadata (mtime, size, name).

    Uses an iterative ``os.scandir`` walk instead of ``pathlib.Path.rglob``:
    ``DirEntry`` objects carry cached ``stat`` results from the directory scan,
    avoiding per-file filesystem round trips. Records are sorted by relative
    path parts to reproduce ``rglob`` + ``sorted()`` ordering exactly
    (case-insensitive on Windows, matching pathlib parity).
    Symlinked files are fingerprinted (matching ``Path.is_file()``), but
    symlinked directories are not recursed into (matching ``Path.rglob``).
    """
    records: list[tuple[str, float, int]] = []
    path_str = str(path)
    base_len = len(path_str) + (0 if path_str.endswith(os.sep) else 1)
    stack = [path_str]

    while stack:
        current = stack.pop()
        try:
            with os.scandir(current) as it:
                entries = list(it)
        except OSError:
            continue
        for entry in entries:
            try:
                if entry.is_dir(follow_symlinks=False):
                    stack.append(entry.path)
                elif entry.is_file(follow_symlinks=True):
                    stat = entry.stat(follow_symlinks=True)
                    rel = entry.path[base_len:].replace(os.sep, "/")
                    records.append((rel, stat.st_mtime, stat.st_size))
            except OSError:
                continue

    if os.name == "nt":
        records.sort(key=lambda r: tuple(p.lower() for p in r[0].split("/")))
    else:
        records.sort(key=lambda r: r[0].split("/"))

    parts = [f"{rel}:{mtime}:{size}" for rel, mtime, size in records]
    return hashlib.sha1("\n".join(parts).encode("utf-8")).hexdigest()
