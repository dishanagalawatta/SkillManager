"""Tests for persistence layer load_cache and save_cache behavior.

The stale-skill filtering is NOT in load_cache — it's at the discovery
level (fingerprint + rebuildCache). These tests verify that load_cache
and save_cache work correctly with the normalization logic.
"""



def _write_cache(tmp_path, skills):
    """Write a cache file with the given skills list."""
    import orjson

    cache_path = tmp_path / "skill_library_index.json"
    data = {"skills": skills, "categories": []}
    cache_path.write_bytes(orjson.dumps(data))
    return cache_path


def test_load_cache_normalizes_project_paths(tmp_path):
    """load_cache normalizes project_path for all skills."""
    from skill_manager.core.persistence import load_cache

    project_root = tmp_path / "my-project"
    skills_dir = project_root / ".agents" / "skills"
    skills_dir.mkdir(parents=True)

    _write_cache(tmp_path, [
        {"name": "Test", "local_path": str(skills_dir / "TestSkill"),
         "project_path": str(project_root), "project_label": "p"},
    ])

    import skill_manager.core.persistence as pers_mod
    original = pers_mod.SKILL_LIBRARY_CACHE_FILE
    pers_mod.SKILL_LIBRARY_CACHE_FILE = str(tmp_path / "skill_library_index.json")
    try:
        loaded = load_cache()
        assert loaded is not None
        assert len(loaded["skills"]) == 1
        assert loaded["skills"][0]["project_path"] == str(skills_dir)
    finally:
        pers_mod.SKILL_LIBRARY_CACHE_FILE = original


def test_load_cache_keeps_all_skills(tmp_path):
    """load_cache returns all skills without filtering by existence."""
    from skill_manager.core.persistence import load_cache

    fake_path = str(tmp_path / "nonexistent-skill")

    _write_cache(tmp_path, [
        {"name": "Fake", "local_path": fake_path, "project_path": "", "project_label": "p"},
    ])

    import skill_manager.core.persistence as pers_mod
    original = pers_mod.SKILL_LIBRARY_CACHE_FILE
    pers_mod.SKILL_LIBRARY_CACHE_FILE = str(tmp_path / "skill_library_index.json")
    try:
        loaded = load_cache()
        assert loaded is not None
        assert len(loaded["skills"]) == 1
        assert loaded["skills"][0]["name"] == "Fake"
    finally:
        pers_mod.SKILL_LIBRARY_CACHE_FILE = original


def test_load_cache_returns_none_when_missing(tmp_path):
    """load_cache returns None when cache file doesn't exist."""
    import skill_manager.core.persistence as pers_mod
    from skill_manager.core.persistence import load_cache
    original = pers_mod.SKILL_LIBRARY_CACHE_FILE
    pers_mod.SKILL_LIBRARY_CACHE_FILE = str(tmp_path / "nonexistent.json")
    try:
        result = load_cache()
        assert result is None
    finally:
        pers_mod.SKILL_LIBRARY_CACHE_FILE = original
