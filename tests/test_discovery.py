import os
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from diskcache import Cache

from skill_manager.core.discovery import (
    DiscoveryService,
    _compute_dir_fingerprint,
)
from skill_manager.core.schemas import CacheState, SkillRecord


@pytest.fixture
def temp_cache_dir(temp_dir):
    cache_dir = temp_dir / "cache"
    cache_dir.mkdir()
    return cache_dir


@pytest.fixture
def disk_cache(temp_cache_dir):
    with Cache(str(temp_cache_dir)) as cache:
        yield cache
        cache.clear()


@pytest.fixture
def service():
    return DiscoveryService(
        sources=[],
        projects=[],
        archive_paths=[],
        starred_paths=[],
        project_aliases={},
    )


def test_compute_dir_fingerprint(temp_dir):
    # 1. Empty dir
    fp1 = _compute_dir_fingerprint(temp_dir)
    assert fp1 != ""

    # 2. Add a skill folder
    skill_dir = temp_dir / "my_skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("content")

    # Wait to ensure mtime change
    time.sleep(0.1)

    fp2 = _compute_dir_fingerprint(temp_dir)
    assert fp2 != fp1

    # 3. Modify internal file and touch subdir
    time.sleep(0.1)
    (skill_dir / "SKILL.md").write_text("updated")
    os.utime(skill_dir, None) # Important for fingerprint to pick up change

    fp3 = _compute_dir_fingerprint(temp_dir)
    assert fp3 != fp2


def test_transform_skill_basic(service):
    raw_skill = {
        "name": "Test Skill",
        "local_path": "/path/to/skill",
        "category": "Test Category",
        "metadata": {"risk": "Low", "source": "Internal"},
    }
    transformed = service.transform_skill(raw_skill, is_package=True)

    # Validate with SkillRecord
    record = SkillRecord.model_validate(transformed)
    assert record.name == "Test Skill"
    assert record.is_package is True
    assert record.risk == "Low"
    assert record.project_label == "Master Library"


def test_transform_skill_star_logic(service):
    # Case 1: Starred in metadata
    s1 = {"local_path": "/p1", "metadata": {"starred": True}}
    assert service.transform_skill(s1, is_package=True)["is_starred"] is True

    # Case 2: Starred in starred_paths
    service.starred_paths = ["/p2"]
    s2 = {"local_path": "/p2", "metadata": {}}
    assert service.transform_skill(s2, is_package=True)["is_starred"] is True


def test_discover_packages_incremental(temp_dir, disk_cache, service):
    source_lib = temp_dir / "master"
    source_lib.mkdir()

    skill1 = source_lib / "skill1"
    skill1.mkdir()
    (skill1 / "SKILL.md").write_text("---\nname: Skill One\n---")

    service.sources = [str(source_lib)]

    def parse_fn(p):
        return {"name": "Skill One", "metadata": {}}

    def cat_fn(n, t, m):
        return {"main_category": "Cat", "sub_category": "Sub"}

    # 1. Initial scan
    skills = service._discover_packages_incremental(disk_cache, parse_fn, cat_fn)
    assert len(skills) == 1
    assert skills[0]["name"] == "Skill One"

    # Verify cache was populated
    # _resolve_resilient_path calls .resolve(), which on Windows resolves short paths
    # like RUNNER~1 to runneradmin. The cache key uses this resolved path.
    import os
    from skill_manager.core.quick_copy import _resolve_resilient_path
    resolved_source = _resolve_resilient_path(str(source_lib))
    fp_key = f"dir_fp:{os.path.normcase(str(resolved_source))}"

    assert disk_cache.get(fp_key) is not None
    assert disk_cache.get(f"pkg_skills:{fp_key}") == skills


@patch("skill_manager.core.discovery.load_cache")
@patch("skill_manager.core.discovery.save_cache")
@patch("skill_manager.core.discovery.get_discovery_cache")
def test_discover_all_pydantic_flow(mock_get_cache, mock_save, mock_load, temp_dir, disk_cache):
    mock_get_cache.return_value.__enter__.return_value = disk_cache
    mock_load.return_value = None

    source_lib = temp_dir / "master"
    source_lib.mkdir()
    skill1 = source_lib / "skill1"
    skill1.mkdir()
    (skill1 / "SKILL.md").write_text("---\nname: Master Skill\ncategory: Tools\n---")

    proj_dir = temp_dir / "project"
    proj_dir.mkdir()
    skill_a = proj_dir / "skillA"
    skill_a.mkdir()
    (skill_a / "SKILL.md").write_text("---\nname: Proj Skill\ncategory: Dev\n---")

    service = DiscoveryService(
        sources=[str(source_lib)],
        projects=[str(proj_dir)],
    )

    result = service.discover_all(use_cache=False)

    # Validate result structure with CacheState
    state = CacheState.model_validate(result)
    assert len(state.skills) >= 2

    skill_names = {s.name for s in state.skills}
    assert "Master Skill" in skill_names
    assert "Proj Skill" in skill_names

    # Ensure categories list is populated
    assert len(state.categories) > 0


def test_scan_single_project_categorization_mapping(temp_dir, service):
    """Verify _scan_single_project maps sub_category -> category correctly.

    Regression: previously used .update(cat_info) which stored sub_category
    key, but transform_skill reads from category key — causing skills to
    appear as 'Uncategorized' in the UI.
    """
    proj_dir = temp_dir / "my_project"
    proj_dir.mkdir()

    skill_dir = proj_dir / "skill1"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("---\nname: Test Skill\n---")

    def parse_fn(p):
        return {"name": "Test Skill", "metadata": {}}

    def cat_fn(n, t, m):
        return {"main_category": "Core Eng", "sub_category": "Testing"}

    res = service._scan_single_project(str(proj_dir), proj_dir, parse_fn, cat_fn)

    assert res is not None
    skill = res["skills"][0]
    assert skill["main_category"] == "Core Eng"
    assert skill["category"] == "Testing"
    assert "sub_category" not in skill


def test_scan_single_project_with_screenshots(temp_dir, service):
    proj_dir = temp_dir / "my_project"
    proj_dir.mkdir()

    # Add a skill
    skill_dir = proj_dir / "skill1"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("---\nname: Real Skill\n---")

    # Add screenshots
    screenshot_dir = proj_dir / ".agents" / "screenshots"
    screenshot_dir.mkdir(parents=True)
    (screenshot_dir / "shot1.png").write_text("data")

    def parse_fn(p):
        return {"name": "Real Skill", "metadata": {}}

    def cat_fn(n, t, m):
        return {"main_category": "C", "sub_category": "S"}

    res = service._scan_single_project(str(proj_dir), proj_dir, parse_fn, cat_fn)

    assert res is not None
    assert len(res["skills"]) == 2  # 1 skill + 1 screenshot

    screenshot = next(s for s in res["skills"] if s.get("is_screenshot"))
    assert screenshot["name"] == "shot1.png"
    assert screenshot["category"] == "Screenshots"


def test_discovery_permission_error_handling(temp_dir, disk_cache, service):
    source_lib = temp_dir / "restricted"
    source_lib.mkdir()

    # Mock iterdir to raise PermissionError
    with patch.object(Path, "iterdir", side_effect=PermissionError("Denied")):
        service.sources = [str(source_lib)]

        # Should not crash
        skills = service._discover_packages_incremental(disk_cache, MagicMock(), MagicMock())
        assert skills == []


def test_discover_single_skill_not_found(service, temp_dir):
    res = service.discover_single_skill(temp_dir / "nonexistent", temp_dir)
    assert res is None


def test_process_command_file_cache(temp_dir, disk_cache, service):
    cmd_file = temp_dir / "test.Codex.md"
    cmd_file.write_text("---\nname: Cmd\n---\nBody")

    project = {"project_label": "P", "project_root": str(temp_dir), "project_path": str(temp_dir)}

    # We need to compute a stable cache key
    stat = cmd_file.stat()
    cache_key = f"cmd:{str(cmd_file)}:{stat.st_mtime}:{stat.st_size}"

    # Pre-populate cache with a mock result
    cached_data = {
        "id": str(cmd_file),
        "name": "Cached Cmd",
        "main_category": "⚙️ System & Workflow",
        "category": "Custom Commands",
        "description": "",
        "local_path": str(cmd_file),
        "project_label": "P",
        "project_root": str(temp_dir),
        "project_path": str(temp_dir),
        "is_starred": False,
        "is_bundle": False,
        "commands": [],
        "is_selected": False,
        "is_archived": False,
        "raw_content": "raw",
        "body_content": "body",
        "risk": "Low",
        "source": "Custom",
        "date": "Unknown",
        "is_package": False,
        "is_source": False,
        "is_command": True,
        "client": "Codex",
    }
    disk_cache.set(cache_key, cached_data)

    # 2. Check cache hit (should return Cached Cmd)
    with patch("skill_manager.core.discovery.parse_command_md") as mock_parse:
        res = service._process_command_file(cmd_file, project, cache=disk_cache)
        assert res["name"] == "Cached Cmd"
        mock_parse.assert_not_called()
