"""
Persistence layer for Skill Manager.
Handles saving and loading of archive, starred, and skill cache.
"""

import contextlib
import json
import os
from pathlib import Path
from typing import Any

from skill_manager.core.config import (
    PROJECT_SKILL_OWNERSHIP_FILE,
    SKILL_LIBRARY_ARCHIVE_FILE,
    SKILL_LIBRARY_CACHE_FILE,
    SKILL_LIBRARY_STARRED_FILE,
    TEMP_COPIES_FILE,
)

# Fields that are expensive to store but read on-demand from disk.
CACHE_EXCLUDED_FIELDS = frozenset({"raw_content", "body_content"})


def save_archive(archive_paths: list[str]) -> bool:
    """Saves archived skill paths to JSON."""
    try:
        with open(SKILL_LIBRARY_ARCHIVE_FILE, "w") as f:
            json.dump(archive_paths, f, indent=4)
        return True
    except Exception as e:
        print(f"Error saving archive: {e}")
        return False


def load_archive() -> list[str]:
    """Loads archived skill paths from JSON."""
    if not os.path.exists(SKILL_LIBRARY_ARCHIVE_FILE):
        return []
    try:
        with open(SKILL_LIBRARY_ARCHIVE_FILE) as f:
            data = json.load(f)
            if isinstance(data, dict):
                return data.get("archived_skills", [])
            return data or []
    except Exception as e:
        print(f"Error loading archive: {e}")
        return []


def save_starred(starred_paths: list[str]) -> bool:
    """Saves starred skill paths to JSON."""
    try:
        with open(SKILL_LIBRARY_STARRED_FILE, "w") as f:
            json.dump(starred_paths, f, indent=4)
        return True
    except Exception as e:
        print(f"Error saving starred: {e}")
        return False


def load_starred() -> list[str]:
    """Loads starred skill paths from JSON."""
    if not os.path.exists(SKILL_LIBRARY_STARRED_FILE):
        return []
    try:
        with open(SKILL_LIBRARY_STARRED_FILE) as f:
            return json.load(f) or []
    except Exception as e:
        print(f"Error loading starred: {e}")
        return []


def load_project_skill_ownership() -> dict[str, dict[str, str]]:
    """Loads project skill package ownership.

    Shape: {normalized_project_skills_path: {folder_name: package_id}}
    """
    if not os.path.exists(PROJECT_SKILL_OWNERSHIP_FILE):
        return {}
    try:
        with open(PROJECT_SKILL_OWNERSHIP_FILE, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception as e:
        print(f"Error loading project skill ownership: {e}")
        return {}


def save_project_skill_ownership(data: dict[str, dict[str, str]]) -> bool:
    try:
        with open(PROJECT_SKILL_OWNERSHIP_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, sort_keys=True)
        return True
    except Exception as e:
        print(f"Error saving project skill ownership: {e}")
        return False


def save_cache(data: dict[str, Any]) -> bool:
    """Saves discovered skills to cache for faster startup.

    Strips raw_content and body_content — these are large per-skill blobs
    read on-demand from disk, not needed in the index cache.
    """
    try:
        slim_data = dict(data)
        if "skills" in slim_data:
            slim_data["skills"] = [
                {k: v for k, v in skill.items() if k not in CACHE_EXCLUDED_FIELDS}
                for skill in slim_data["skills"]
            ]

        # print(f"[CACHE] Saving {len(slim_data.get('skills', []))} skills to {SKILL_LIBRARY_CACHE_FILE}...")
        with open(SKILL_LIBRARY_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(slim_data, f, indent=2, default=str)
        return True
    except Exception as e:
        print(f"Error saving cache: {e}")
        return False


def load_cache() -> dict[str, Any] | None:
    """Loads skills from cache. Returns None if missing or corrupted."""
    cache_path = Path(SKILL_LIBRARY_CACHE_FILE)
    if not cache_path.exists():
        return None
    try:
        with open(cache_path, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, UnicodeDecodeError, OSError) as e:
        print(f"[CACHE] Corrupted cache ({e}).")
        with contextlib.suppress(BaseException):
            cache_path.unlink()
        return None


def patch_cache_remove(paths_to_remove: list[str]) -> int:
    """Surgically removes entries from on-disk cache without full rescan.
    Returns the number of removed entries.
    """
    try:
        cache_path = Path(SKILL_LIBRARY_CACHE_FILE)
        if not cache_path.exists():
            return 0

        path_set = set(paths_to_remove)
        with open(cache_path, encoding="utf-8") as f:
            data = json.load(f)

        original_count = len(data.get("skills", []))
        data["skills"] = [s for s in data.get("skills", []) if s.get("local_path") not in path_set]
        removed = original_count - len(data["skills"])

        if removed > 0:
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=str)

        return removed
    except Exception as exc:
        print(f"[CACHE] Patch failed: {exc}")
        return 0


def patch_cache_add(
    new_skills: list[dict[str, Any]], projects_state: list[dict[str, Any]] = None
) -> int:
    """Surgically adds or updates entries in the on-disk cache without full rescan.
    Returns the number of added or updated entries.
    """
    try:
        cache_path = Path(SKILL_LIBRARY_CACHE_FILE)
        if not cache_path.exists():
            return 0

        with open(cache_path, encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, dict):
            return 0

        if "skills" not in data:
            data["skills"] = []
        if "projects" not in data:
            data["projects"] = []

        # Strip large fields from new_skills
        clean_new_skills = []
        for s in new_skills:
            clean_s = {k: v for k, v in s.items() if k not in CACHE_EXCLUDED_FIELDS}
            clean_new_skills.append(clean_s)

        # Update skills list
        skills_map = {s.get("local_path"): s for s in data["skills"]}
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
            {
                p["project_label"]
                for p in data.get("projects", [])
                if p.get("project_label")
            }
        )

        # Update status
        num_skills = len(data["skills"])
        num_projects = len(data.get("projects", []))
        data["status"] = (
            f"Found {num_skills} skills in master library ({num_projects} projects)"
        )

        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)

        return updated_count
    except Exception as exc:
        print(f"[CACHE] Patch add failed: {exc}")
        return 0



def save_temp_registry(paths: list[str]) -> None:
    """Saves the list of temporary copy paths to the registry."""
    try:
        with open(TEMP_COPIES_FILE, "w") as f:
            json.dump({"temp_paths": paths}, f, indent=4)
    except Exception as e:
        print(f"Error saving temp registry: {e}")


def load_temp_registry() -> list[str]:
    """Loads the list of temporary copy paths from the registry."""
    if not os.path.exists(TEMP_COPIES_FILE):
        return []
    try:
        with open(TEMP_COPIES_FILE) as f:
            data = json.load(f)
            return data.get("temp_paths", [])
    except Exception as e:
        print(f"Error loading temp registry: {e}")
        return []
