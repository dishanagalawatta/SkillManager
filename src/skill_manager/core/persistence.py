"""
Persistence layer for Skill Manager.
Handles saving and loading of archive, starred, and skill cache.
"""

import contextlib
import logging
import os
from pathlib import Path
from typing import Any

import orjson

from skill_manager.core.config import (
    PACKAGE_SKILL_INVENTORY_FILE,
    PROJECT_SKILL_OWNERSHIP_FILE,
    SKILL_LIBRARY_ARCHIVE_FILE,
    SKILL_LIBRARY_CACHE_FILE,
    SKILL_LIBRARY_STARRED_FILE,
    TEMP_COPIES_FILE,
    TEMP_SCREENSHOTS_FILE,
)
from skill_manager.core.schemas import CacheState
from skill_manager.utils.cooperative_lock import FileLock, LockTimeout

logger = logging.getLogger(__name__)

# Fields that are expensive to store but read on-demand from disk.
CACHE_EXCLUDED_FIELDS = frozenset({"raw_content", "body_content"})


def _atomic_write_json(file_path: str | Path, data: Any, indent: bool = True) -> bool:
    """Writes JSON to a temporary file then renames it for atomicity using orjson."""
    import time

    file_path = str(file_path)
    temp_path = f"{file_path}.tmp"
    max_retries = 3
    for attempt in range(max_retries):
        try:
            option = orjson.OPT_INDENT_2 if indent else 0
            content = orjson.dumps(
                data, option=option | orjson.OPT_SERIALIZE_DATACLASS | orjson.OPT_APPEND_NEWLINE
            )
            with open(temp_path, "wb") as f:
                f.write(content)
            os.replace(temp_path, file_path)
            return True
        except OSError as e:
            # WinError 32: process cannot access the file (file in use)
            # WinError 2: file not found (temp file removed by another process)
            if e.winerror in (32, 2) and attempt < max_retries - 1:
                wait = 0.05 * (2**attempt)  # 50ms, 100ms, 200ms
                logger.warning(
                    "Atomic write to %s hit WinError %d (attempt %d/%d), retrying in %.0fms",
                    file_path,
                    e.winerror,
                    attempt + 1,
                    max_retries,
                    wait * 1000,
                )
                time.sleep(wait)
                continue
            logger.warning("Error atomic writing to %s: %s", file_path, e)
            with contextlib.suppress(OSError):
                if os.path.exists(temp_path):
                    os.remove(temp_path)
            return False
        except Exception as e:
            logger.warning("Error atomic writing to %s: %s", file_path, e)
            with contextlib.suppress(OSError):
                if os.path.exists(temp_path):
                    os.remove(temp_path)
            return False
    return False


def save_archive(archive_paths: list[str]) -> bool:
    """Saves archived skill paths to JSON."""
    return _atomic_write_json(SKILL_LIBRARY_ARCHIVE_FILE, archive_paths)


def load_archive() -> list[str]:
    """Loads archived skill paths from JSON."""
    if not os.path.exists(SKILL_LIBRARY_ARCHIVE_FILE):
        return []
    try:
        with open(SKILL_LIBRARY_ARCHIVE_FILE, "rb") as f:
            data = orjson.loads(f.read())
            if isinstance(data, dict):
                return data.get("archived_skills", [])
            return data or []
    except Exception as e:
        logger.warning("Error loading archive: %s", e)
        return []


def save_starred(starred_paths: list[str]) -> bool:
    """Saves starred skill paths to JSON."""
    return _atomic_write_json(SKILL_LIBRARY_STARRED_FILE, starred_paths)


def load_starred() -> list[str]:
    """Loads starred skill paths from JSON."""
    if not os.path.exists(SKILL_LIBRARY_STARRED_FILE):
        return []
    try:
        with open(SKILL_LIBRARY_STARRED_FILE, "rb") as f:
            return orjson.loads(f.read()) or []
    except Exception as e:
        logger.warning("Error loading starred: %s", e)
        return []


def load_project_skill_ownership() -> dict[str, dict[str, str]]:
    """Loads project skill package ownership.

    Shape: {normalized_project_skills_path: {folder_name: package_id}}
    """
    if not os.path.exists(PROJECT_SKILL_OWNERSHIP_FILE):
        return {}
    try:
        with open(PROJECT_SKILL_OWNERSHIP_FILE, "rb") as f:
            data = orjson.loads(f.read())
        return data if isinstance(data, dict) else {}
    except Exception as e:
        logger.warning("Error loading project skill ownership: %s", e)
        return {}


def save_project_skill_ownership(data: dict[str, dict[str, str]]) -> bool:
    return _atomic_write_json(PROJECT_SKILL_OWNERSHIP_FILE, data)


def load_package_skill_inventory() -> dict[str, Any]:
    """Loads package skill inventory.

    Shape: {package_id: {"configured_package_path": str,
                         "resolved_package_path": str,
                         "skills": {folder_name: skill_record}}}
    """
    if not os.path.exists(PACKAGE_SKILL_INVENTORY_FILE):
        return {}
    try:
        with open(PACKAGE_SKILL_INVENTORY_FILE, "rb") as f:
            data = orjson.loads(f.read())
        return data if isinstance(data, dict) else {}
    except Exception as e:
        logger.warning("Error loading package skill inventory: %s", e)
        return {}


def save_package_skill_inventory(data: dict[str, Any]) -> bool:
    return _atomic_write_json(PACKAGE_SKILL_INVENTORY_FILE, data)


def _normalize_skill_project_path(skill: dict[str, Any]) -> dict[str, Any]:
    """Normalize a skill's project_path through get_skills_dir for consistency."""
    pp = skill.get("project_path")
    if pp:
        from skill_manager.core.copier import get_skills_dir

        skill["project_path"] = str(get_skills_dir(pp))
    return skill


def save_cache(data: dict[str, Any]) -> bool:
    """Saves discovered skills to cache for faster startup.

    Strips raw_content and body_content — these are large per-skill blobs
    read on-demand from disk, not needed in the index cache.
    Normalizes project_path through get_skills_dir before writing.

    Uses a cross-platform file lock so that multiple instances writing
    concurrently do not corrupt the JSON cache.
    """
    try:
        slim_data = dict(data)
        if "skills" in slim_data:
            slim_data["skills"] = [
                _normalize_skill_project_path(
                    {k: v for k, v in skill.items() if k not in CACHE_EXCLUDED_FIELDS}
                )
                for skill in slim_data["skills"]
            ]
        with FileLock(SKILL_LIBRARY_CACHE_FILE):
            return _atomic_write_json(SKILL_LIBRARY_CACHE_FILE, slim_data)
    except LockTimeout:
        logger.warning("[CACHE] Lock timeout on save_cache — skipping write (peer is active)")
        return False
    except Exception as e:
        logger.warning("Error saving cache: %s", e)
        return False


def load_cache() -> dict[str, Any] | None:
    """Loads skills from cache. Returns None if missing or corrupted.

    Normalizes each skill's project_path in-memory on load so the model
    receives correct paths even if the on-disk cache is stale.
    """
    cache_path = Path(SKILL_LIBRARY_CACHE_FILE)
    if not cache_path.exists():
        return None
    try:
        with open(cache_path, "rb") as f:
            data = orjson.loads(f.read())
        validated = CacheState.model_validate(data).model_dump()
        # Normalize project_path in-memory for all skills
        if "skills" in validated:
            validated["skills"] = [_normalize_skill_project_path(s) for s in validated["skills"]]
        return validated
    except (orjson.JSONDecodeError, UnicodeDecodeError, OSError) as e:
        logger.warning("[CACHE] Corrupted cache (%s).", e)
        with contextlib.suppress(BaseException):
            cache_path.unlink()
        return None


def patch_cache_remove(paths_to_remove: list[str]) -> int:
    """Surgically removes entries from on-disk cache without full rescan.
    Returns the number of removed entries.

    Uses a cross-platform file lock for multi-instance safety.
    """
    try:
        cache_path = Path(SKILL_LIBRARY_CACHE_FILE)
        if not cache_path.exists():
            return 0

        path_set = set(paths_to_remove)
        with FileLock(SKILL_LIBRARY_CACHE_FILE):
            with open(cache_path, "rb") as f:
                data = orjson.loads(f.read())

            original_count = len(data.get("skills", []))
            data["skills"] = [
                s for s in data.get("skills", []) if s.get("local_path") not in path_set
            ]
            removed = original_count - len(data["skills"])

            if removed > 0:
                _atomic_write_json(SKILL_LIBRARY_CACHE_FILE, data)

            return removed
    except LockTimeout:
        logger.warning("[CACHE] Lock timeout on patch_cache_remove — skipping (peer is active)")
        return 0
    except Exception as exc:
        logger.warning("[CACHE] Patch failed: %s", exc)
        return 0


def patch_cache_add(
    new_skills: list[dict[str, Any]], projects_state: list[dict[str, Any]] | None = None
) -> int:
    """Surgically adds or updates entries in the on-disk cache without full rescan.
    Returns the number of added or updated entries.

    Uses a cross-platform file lock for multi-instance safety.
    """
    try:
        cache_path = Path(SKILL_LIBRARY_CACHE_FILE)
        if not cache_path.exists():
            return 0

        with FileLock(SKILL_LIBRARY_CACHE_FILE):
            with open(cache_path, "rb") as f:
                data = orjson.loads(f.read())

            if not isinstance(data, dict):
                return 0

            if "skills" not in data:
                data["skills"] = []
            if "projects" not in data:
                data["projects"] = []

            # Strip large fields from new_skills and normalize project_path
            clean_new_skills = []
            for s in new_skills:
                clean_s = {k: v for k, v in s.items() if k not in CACHE_EXCLUDED_FIELDS}
                _normalize_skill_project_path(clean_s)
                clean_new_skills.append(clean_s)

            # Update skills list — also normalize existing cache entries
            skills_map = {
                _normalize_skill_project_path(s).get("local_path"): s for s in data["skills"]
            }
            updated_count = 0
            for s in clean_new_skills:
                path = s.get("local_path")
                if path:
                    skills_map[path] = s
                    updated_count += 1
            data["skills"] = list(skills_map.values())

            # Update projects state if provided
            if projects_state:
                projects_map = {p.get("project_path"): p for p in data["projects"]}
                for p in projects_state:
                    path = p.get("project_path")
                    if path:
                        # Clean the skills inside project
                        cleaned_p = dict(p)
                        if "skills" in cleaned_p:
                            cleaned_p["skills"] = [
                                {k: v for k, v in skill.items() if k not in CACHE_EXCLUDED_FIELDS}
                                for skill in cleaned_p["skills"]
                            ]
                        projects_map[path] = cleaned_p
                data["projects"] = list(projects_map.values())

            # Re-compute categories and project_labels
            data["categories"] = sorted(
                {s["category"] for s in data["skills"] if s.get("category")}
            )
            data["project_labels"] = sorted(
                {p["project_label"] for p in data.get("projects", []) if p.get("project_label")}
            )

            # Update status
            num_skills = len(data["skills"])
            num_projects = len(data.get("projects", []))
            data["status"] = (
                f"Found {num_skills} skills in master library ({num_projects} projects)"
            )

            _atomic_write_json(SKILL_LIBRARY_CACHE_FILE, data)

            return updated_count
    except LockTimeout:
        logger.warning("[CACHE] Lock timeout on patch_cache_add — skipping (peer is active)")
        return 0
    except Exception as exc:
        logger.warning("[CACHE] Patch add failed: %s", exc)
        return 0


def save_temp_registry(paths: list[str]) -> None:
    """Saves the list of temporary copy paths to the registry."""
    _atomic_write_json(TEMP_COPIES_FILE, {"temp_paths": paths})


def load_temp_registry() -> list[str]:
    """Loads the list of temporary copy paths from the registry."""
    if not os.path.exists(TEMP_COPIES_FILE):
        return []
    try:
        with open(TEMP_COPIES_FILE, "rb") as f:
            data = orjson.loads(f.read())
            return data.get("temp_paths", [])
    except Exception as e:
        logger.warning("Error loading temp registry: %s", e)
        return []


def save_temp_screenshots_registry(paths: list[str]) -> None:
    """Saves the list of temporary screenshot paths to the registry."""
    _atomic_write_json(TEMP_SCREENSHOTS_FILE, {"temp_paths": paths})


def load_temp_screenshots_registry() -> list[str]:
    """Loads the list of temporary screenshot paths from the registry."""
    if not os.path.exists(TEMP_SCREENSHOTS_FILE):
        return []
    try:
        with open(TEMP_SCREENSHOTS_FILE, "rb") as f:
            data = orjson.loads(f.read())
            return data.get("temp_paths", [])
    except Exception as e:
        logger.warning("Error loading temp screenshots registry: %s", e)
        return []
