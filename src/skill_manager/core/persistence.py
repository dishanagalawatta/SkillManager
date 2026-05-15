"""
Persistence layer for Skill Manager.
Handles saving and loading of archive, essentials, and skill cache.
"""
import contextlib
import json
import os
from pathlib import Path
from typing import Any

from skill_manager.core.config import (
    SKILL_LIBRARY_ARCHIVE_FILE,
    SKILL_LIBRARY_CACHE_FILE,
    SKILL_LIBRARY_ESSENTIALS_FILE,
)

# Fields that are expensive to store but read on-demand from disk.
CACHE_EXCLUDED_FIELDS = frozenset({"raw_content", "body_content"})

def save_archive(archive_paths: list[str]) -> bool:
    """Saves archived skill paths to JSON."""
    try:
        with open(SKILL_LIBRARY_ARCHIVE_FILE, 'w') as f:
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

def save_essentials(essential_paths: list[str]) -> bool:
    """Saves essential skill paths to JSON."""
    try:
        with open(SKILL_LIBRARY_ESSENTIALS_FILE, 'w') as f:
            json.dump(essential_paths, f, indent=4)
        return True
    except Exception as e:
        print(f"Error saving essentials: {e}")
        return False

def load_essentials() -> list[str]:
    """Loads essential skill paths from JSON."""
    if not os.path.exists(SKILL_LIBRARY_ESSENTIALS_FILE):
        return []
    try:
        with open(SKILL_LIBRARY_ESSENTIALS_FILE) as f:
            return json.load(f) or []
    except Exception as e:
        print(f"Error loading essentials: {e}")
        return []

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
        with open(SKILL_LIBRARY_CACHE_FILE, 'w', encoding='utf-8') as f:
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
        with open(cache_path, encoding='utf-8') as f:
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
