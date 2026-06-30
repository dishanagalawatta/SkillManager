"""Tests for cache persistence project_path normalization.

Verifies that save_cache, load_cache, and patch_cache_add normalize
project_path through get_skills_dir for consistency.
"""

from unittest.mock import patch

from skill_manager.core.persistence import (
    _normalize_skill_project_path,
    load_cache,
    patch_cache_add,
    save_cache,
)


def test_normalize_skill_project_path_root(tmp_path):
    """_normalize_skill_project_path rewrites root path to .agents/skills."""
    project_root = tmp_path / "my-project"
    skills_dir = project_root / ".agents" / "skills"
    skills_dir.mkdir(parents=True)

    skill = {"project_path": str(project_root)}
    result = _normalize_skill_project_path(skill)
    assert result["project_path"] == str(skills_dir)


def test_normalize_skill_project_path_already_normalized(tmp_path):
    """_normalize_skill_project_path keeps already-normalized path unchanged."""
    project_root = tmp_path / "my-project"
    skills_dir = project_root / ".agents" / "skills"
    skills_dir.mkdir(parents=True)

    skill = {"project_path": str(skills_dir)}
    result = _normalize_skill_project_path(skill)
    assert result["project_path"] == str(skills_dir)


def test_normalize_skill_project_path_no_path():
    """_normalize_skill_project_path handles skill with no project_path."""
    skill = {"name": "TestSkill"}
    result = _normalize_skill_project_path(skill)
    assert result == {"name": "TestSkill"}


def test_save_cache_normalizes_project_paths(tmp_path):
    """save_cache normalizes project_path before writing to disk."""
    project_root = tmp_path / "my-project"
    skills_dir = project_root / ".agents" / "skills"
    skills_dir.mkdir(parents=True)

    cache_file = tmp_path / "test_cache.json"
    data = {
        "skills": [
            {
                "name": "TestSkill",
                "local_path": str(skills_dir / "TestSkill"),
                "project_path": str(project_root),  # root path
                "project_label": "TestSkill",
            }
        ],
        "categories": ["General"],
        "status": "test",
    }

    with patch("skill_manager.core.persistence.SKILL_LIBRARY_CACHE_FILE", str(cache_file)):
        result = save_cache(data)

    assert result is True
    assert cache_file.exists()

    import orjson

    with open(cache_file, "rb") as f:
        saved = orjson.loads(f.read())

    assert saved["skills"][0]["project_path"] == str(skills_dir)


def test_load_cache_normalizes_project_paths(tmp_path):
    """load_cache normalizes project_path in-memory on load."""
    project_root = tmp_path / "my-project"
    skills_dir = project_root / ".agents" / "skills"
    skills_dir.mkdir(parents=True)

    cache_file = tmp_path / "test_cache.json"
    cache_data = {
        "skills": [
            {
                "name": "TestSkill",
                "local_path": str(skills_dir / "TestSkill"),
                "project_path": str(project_root),  # root path in cache
                "project_label": "TestSkill",
                "project_root": "",
                "skill_md_path": "",
                "is_starred": False,
                "is_archived": False,
                "is_bundle": False,
                "is_command": False,
                "is_package": False,
                "is_screenshot": False,
                "category": "General",
                "description": "",
                "risk": "Unknown",
                "source": "Unknown",
                "date": "Unknown",
                "client": "",
                "main_category": "System",
                "tags": [],
            }
        ],
        "categories": ["General"],
        "project_labels": [],
        "status": "test",
    }

    import orjson

    with open(cache_file, "wb") as f:
        f.write(orjson.dumps(cache_data))

    with patch("skill_manager.core.persistence.SKILL_LIBRARY_CACHE_FILE", str(cache_file)):
        loaded = load_cache()

    assert loaded is not None
    assert loaded["skills"][0]["project_path"] == str(skills_dir)


def test_patch_cache_add_normalizes_paths(tmp_path):
    """patch_cache_add normalizes project_path in both new and existing entries."""
    project_root = tmp_path / "my-project"
    skills_dir = project_root / ".agents" / "skills"
    skills_dir.mkdir(parents=True)

    cache_file = tmp_path / "test_cache.json"
    cache_data = {
        "skills": [
            {
                "name": "OldSkill",
                "local_path": str(skills_dir / "OldSkill"),
                "project_path": str(project_root),  # root path
                "project_label": "OldSkill",
                "category": "General",
            }
        ],
        "categories": ["General"],
        "project_labels": [],
        "status": "test",
    }

    import orjson

    with open(cache_file, "wb") as f:
        f.write(orjson.dumps(cache_data))

    new_skills = [
        {
            "name": "NewSkill",
            "local_path": str(skills_dir / "NewSkill"),
            "project_path": str(project_root),  # root path
            "project_label": "NewSkill",
            "category": "General",
        }
    ]

    with patch("skill_manager.core.persistence.SKILL_LIBRARY_CACHE_FILE", str(cache_file)):
        count = patch_cache_add(new_skills)

    assert count == 1

    with open(cache_file, "rb") as f:
        patched = orjson.loads(f.read())

    # Both old and new skills should have normalized paths
    for skill in patched["skills"]:
        assert skill["project_path"] == str(skills_dir), (
            f"project_path not normalized for {skill['name']}: {skill['project_path']}"
        )
