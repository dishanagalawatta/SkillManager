"""Discovery pipeline tests — consolidated suite.

Merged per Phase 5 of the test consolidation plan from:
- test_discovery.py (canonical)
- test_discovery_fingerprint_child_hash.py (child-name hash detection)
- test_discovery_fp.py (fingerprint memoization)
- test_discovery_verifies_paths.py (post-scan path verification)
- test_force_full_scan.py (force_full_scan parameter)
- test_discovery_sdet.py (DiscoveryController SDET contract)
"""

import hashlib
import os
import shutil
import sys
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from diskcache import Cache

from skill_manager.controllers.discovery_controller import DiscoveryController
from skill_manager.core import discovery
from skill_manager.core.discovery import (
    DiscoveryService,
    _hash_child_names,
    compute_dir_fingerprint,
)
from skill_manager.core.models.entities import PreparedModelState, Skill
from skill_manager.core.quick_copy import resolve_resilient_path
from skill_manager.core.schemas import CacheState, SkillRecord

# ── Fixtures ────────────────────────────────────────────────────────────


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


@pytest.fixture
def sdet_app():
    """SDET-specifc mock app (shadows nothing: DiscoveryController needs these attrs)."""
    app = MagicMock()
    app._sources = ["/src"]
    app._update_packages = []
    app._projects = []
    app._archive_paths = []
    app._starred_paths = []
    app._project_aliases = {}
    app._categories = []
    app._client_format = "Antigravity"
    app._current_project_label = ""
    app._library_model = MagicMock()
    app._quick_copy_model = MagicMock()
    app.task_runner = MagicMock()
    app.isTesting = True
    return app


@pytest.fixture
def controller(sdet_app):
    return DiscoveryController(sdet_app)


# ── Helpers ─────────────────────────────────────────────────────────────


def _make_skill_dir(parent: Path, name: str) -> Path:
    """Create `<parent>/<name>/SKILL.md` and return the skill subdir."""
    skill = parent / name
    skill.mkdir(parents=True, exist_ok=True)
    (skill / "SKILL.md").write_text(f"# {name}\n", encoding="utf-8")
    return skill


def _parse_test(path: str) -> dict:
    return {"name": "test", "description": ""}


def _parse_by_parent(path: str) -> dict:
    return {"name": Path(path).parent.name, "description": ""}


def _parse_skill(path: str) -> dict:
    return {"name": "test", "description": ""}


def _parse_skill_pkg(path: str) -> dict:
    return {"name": "pkg", "description": ""}


def _parse_skill_by_parent(path: str) -> dict:
    return {"name": Path(path).parent.name, "description": ""}


def _cat_test(name: str, text: str, meta: dict) -> dict:
    return {"main_category": "Test", "sub_category": ""}


def _cat_pkg(name: str, text: str, meta: dict) -> dict:
    return {"main_category": "Pkg", "sub_category": ""}


# ── compute_dir_fingerprint ─────────────────────────────────────────────


def test_compute_dir_fingerprint(temp_dir):
    # 1. Empty dir
    fp1 = compute_dir_fingerprint(temp_dir)
    assert fp1 != ""

    # 2. Add a skill folder
    skill_dir = temp_dir / "my_skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("content")

    # Wait to ensure mtime change
    time.sleep(0.1)

    fp2 = compute_dir_fingerprint(temp_dir)
    assert fp2 != fp1

    # 3. Modify internal file and touch subdir
    time.sleep(0.1)
    (skill_dir / "SKILL.md").write_text("updated")
    os.utime(skill_dir, None)  # Important for fingerprint to pick up change

    fp3 = compute_dir_fingerprint(temp_dir)
    assert fp3 != fp2


def test_fingerprint_includes_child_names_hash_component():
    """Fingerprint changes when child directory names change."""
    tmp = Path(__file__).parent / "test_fingerprint_tmp"  # noqa: S100

    # Create dir with one child
    d = tmp / "base"
    d.mkdir(parents=True, exist_ok=True)
    (d / "alpha").mkdir(exist_ok=True)

    fp1 = compute_dir_fingerprint(d)

    # Add a new child
    (d / "bravo").mkdir(exist_ok=True)
    fp2 = compute_dir_fingerprint(d)

    assert fp1 != fp2, "Fingerprint should change when child dir is added"

    # Cleanup
    shutil.rmtree(tmp, ignore_errors=True)


def test_fingerprint_changes_when_child_dir_added(tmp_path):
    """Adding a child directory changes the fingerprint."""
    d = tmp_path / "dir"
    d.mkdir()
    fp_before = compute_dir_fingerprint(d)

    (d / "new-child").mkdir()
    fp_after = compute_dir_fingerprint(d)

    assert fp_before != fp_after


def test_fingerprint_changes_when_child_dir_deleted(tmp_path):
    """Deleting a child directory changes the fingerprint (the brainstorming case)."""
    d = tmp_path / "dir"
    d.mkdir()
    (d / "child-a").mkdir()
    (d / "child-b").mkdir()

    fp_before = compute_dir_fingerprint(d)

    # Delete one child (simulates removing brainstorming skill)
    shutil.rmtree(d / "child-a")

    fp_after = compute_dir_fingerprint(d)

    assert fp_before != fp_after, "Fingerprint MUST change when a child dir is deleted"


def test_fingerprint_changes_when_child_dir_renamed(tmp_path):
    """Renaming a child directory changes the fingerprint."""
    d = tmp_path / "dir"
    d.mkdir()
    (d / "old-name").mkdir()

    fp_before = compute_dir_fingerprint(d)

    (d / "old-name").rename(d / "new-name")
    fp_after = compute_dir_fingerprint(d)

    assert fp_before != fp_after


def test_fingerprint_unchanged_for_unchanged_dir(tmp_path):
    """Fingerprint stays the same when nothing changes."""
    d = tmp_path / "dir"
    d.mkdir()
    (d / "child-a").mkdir()
    (d / "child-b").mkdir()

    fp1 = compute_dir_fingerprint(d)
    fp2 = compute_dir_fingerprint(d)

    assert fp1 == fp2


def test_hash_child_names_sorted():
    """_hash_child_names returns same hash regardless of filesystem iteration order."""
    tmp = Path(__file__).parent / "test_hash_tmp"  # noqa: S100
    d = tmp / "dir"
    d.mkdir(parents=True, exist_ok=True)
    (d / "bravo").mkdir(exist_ok=True)
    (d / "alpha").mkdir(exist_ok=True)

    h1 = _hash_child_names(d)
    h2 = _hash_child_names(d)

    assert h1 == h2, "Hash should be deterministic"
    assert len(h1) == 16

    shutil.rmtree(tmp, ignore_errors=True)


def test_hash_child_names_empty_dir(tmp_path):
    """_hash_child_names returns empty string for empty dir on error, or hash of empty string."""
    h = _hash_child_names(tmp_path)
    # Empty dir: sorted names = [], join = "", sha1 of "" = e3b0c44298fc...
    expected = hashlib.sha1(b"").hexdigest()[:16]
    assert h == expected


# ── Fingerprint memoization ─────────────────────────────────────────────


def test_fingerprint_is_stable_across_calls(tmp_path: Path) -> None:
    """Two calls on an unchanged dir return the same fingerprint."""
    d = tmp_path / "src"
    d.mkdir()
    _make_skill_dir(d, "alpha")
    _make_skill_dir(d, "bravo")

    fp1 = compute_dir_fingerprint(d)
    fp2 = compute_dir_fingerprint(d)

    assert fp1 == fp2
    assert len(fp1) == len(hashlib.md5(b"").hexdigest())


def test_fingerprint_matches_unmemoized_formula(tmp_path: Path) -> None:
    """Fingerprint equals md5 of the documented raw format string."""
    d = tmp_path / "src"
    d.mkdir()
    _make_skill_dir(d, "alpha")
    _make_skill_dir(d, "bravo")

    # Pin mtimes so the stat reads below and the re-reads inside
    # compute_dir_fingerprint see identical values. Windows NTFS delays
    # directory mtime updates after mutations, which made this test flaky
    # on CI (Py 3.13) when the two reads straddled a metadata flush.
    fixed_mtime = 1_700_000_000.0
    for child in d.iterdir():
        os.utime(child, (fixed_mtime, fixed_mtime))
    os.utime(d, (fixed_mtime, fixed_mtime))

    # Compute the expected raw string using only the public building blocks,
    # independent of the memoization path inside compute_dir_fingerprint.
    stat = d.stat()
    skill_dirs = [c for c in d.iterdir() if c.is_dir() and (c / "SKILL.md").is_file()]
    skill_count = len(skill_dirs)
    max_sub_mtime = max(s.stat().st_mtime for s in skill_dirs) if skill_dirs else 0.0
    child_names_hash = _hash_child_names(d)
    expected_raw = (
        f"{stat.st_mtime}:{stat.st_size}:{skill_count}:{max_sub_mtime}:{child_names_hash}"
    )
    expected_fp = hashlib.md5(expected_raw.encode()).hexdigest()

    assert compute_dir_fingerprint(d) == expected_fp


def test_second_call_hits_memo_and_skips_md5(tmp_path: Path) -> None:
    """On a memo hit the cached fingerprint is reused: the md5 recompute
    is skipped, while the child-name hash IS re-verified (on Windows the
    stat prefix alone can be stale after directory-entry mutations).
    """
    d = tmp_path / "src"
    d.mkdir()
    _make_skill_dir(d, "alpha")

    # Prime the memo.
    fp1 = compute_dir_fingerprint(d)
    assert fp1, "Baseline fingerprint should be non-empty"

    # Patch hashlib.md5 with a tracking wrapper: the fingerprint md5 is the
    # step the memo must skip on a hit. (_hash_child_names uses sha1, so
    # md5 calls come only from the fingerprint computation.)
    calls = {"md5": 0}
    real_md5 = hashlib.md5

    def wrapper(data: bytes):
        calls["md5"] += 1
        return real_md5(data)

    with patch.object(hashlib, "md5", side_effect=wrapper):
        fp2 = compute_dir_fingerprint(d)

    assert fp1 == fp2, "Memo hit must return the same fingerprint"
    assert calls["md5"] == 0, (
        f"md5 recompute must NOT run on a memo hit; ran {calls['md5']} time(s)"
    )


def test_memo_miss_when_dir_changes(tmp_path: Path) -> None:
    """When a new subdir with SKILL.md is added, the memo is invalidated,
    _hash_child_names IS called again, and the fingerprint changes.
    """
    d = tmp_path / "src"
    d.mkdir()
    _make_skill_dir(d, "alpha")

    fp_before = compute_dir_fingerprint(d)

    real = _hash_child_names
    calls = {"n": 0}

    def wrapper(p: Path) -> str:
        calls["n"] += 1
        return real(p)

    # Mutate the dir: add a new skill subdir, which shifts skill_count and
    # the parent's mtime/size (and possibly max_sub_mtime). Either way the
    # prefix tuple changes and we expect a cache miss.
    _make_skill_dir(d, "bravo")

    with patch.object(discovery, "_hash_child_names", side_effect=wrapper):
        fp_after = compute_dir_fingerprint(d)

    assert fp_before != fp_after, "Fingerprint MUST change after a real mutation"
    assert calls["n"] == 1, (
        f"_hash_child_names must run exactly once on a memo miss; ran {calls['n']} time(s)"
    )

    # And a third call (no further mutation) should hit the memo again:
    # same fingerprint, with the child-name hash re-verified exactly once.
    calls["n"] = 0
    with patch.object(discovery, "_hash_child_names", side_effect=wrapper):
        fp_after_again = compute_dir_fingerprint(d)
    assert fp_after_again == fp_after
    assert calls["n"] == 1, f"Hash must be re-verified once on a memo hit; ran {calls['n']} time(s)"


def test_memo_key_is_normcase_insensitive(tmp_path: Path) -> None:
    """On case-insensitive filesystems (Windows), the memo must be keyed
    by normcase so that 'Foo' and 'foo' share a cache entry.

    Skipped on case-sensitive filesystems (Linux) where ``Path(str(d).upper())``
    refers to a non-existent directory.
    """
    # Detect case-insensitive filesystem: on Linux (the CI host), /tmp is
    # almost always case-sensitive, so the uppercased path won't exist and
    # compute_dir_fingerprint returns ''.  Skip on case-sensitive FS.
    if sys.platform != "win32" and not Path(str(tmp_path).upper()).exists():
        pytest.skip("case-insensitive normcase test requires case-insensitive FS")

    d = tmp_path / "src"
    d.mkdir()
    _make_skill_dir(d, "alpha")

    fp1 = compute_dir_fingerprint(d)

    # Same path, different case in the string form — normcase collapses it.
    fp2 = compute_dir_fingerprint(Path(str(d).upper()))

    assert fp1 == fp2


def test_memo_does_not_leak_across_distinct_dirs(tmp_path: Path) -> None:
    """Two different directories must not share a memo entry."""
    a = tmp_path / "a"
    b = tmp_path / "b"
    a.mkdir()
    b.mkdir()
    _make_skill_dir(a, "x")
    _make_skill_dir(b, "y")

    fp_a = compute_dir_fingerprint(a)
    fp_b = compute_dir_fingerprint(b)

    assert fp_a != fp_b
    # Second calls on each must still return their own value (no cross-pollution).
    assert compute_dir_fingerprint(a) == fp_a
    assert compute_dir_fingerprint(b) == fp_b


# ── Transform & incremental discovery ───────────────────────────────────


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
    skills = service.discover_packages_incremental(disk_cache, parse_fn, cat_fn)
    assert len(skills) == 1
    assert skills[0]["name"] == "Skill One"

    # Verify cache was populated
    # Use resolved path to match production code's normalization (resolves 8.3 short names on Windows)
    resolved = resolve_resilient_path(str(source_lib))
    fp_key = f"pkg_dir_fp:{os.path.normcase(str(resolved))}"
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
    snap_dir = proj_dir / ".agents" / "screenshots"
    snap_dir.mkdir(parents=True)
    (snap_dir / "shot1.png").write_text("data")

    def parse_fn(p):
        return {"name": "Real Skill", "metadata": {}}

    def cat_fn(n, t, m):
        return {"main_category": "C", "sub_category": "S"}

    res = service._scan_single_project(str(proj_dir), proj_dir, parse_fn, cat_fn)

    assert res is not None
    assert len(res["skills"]) == 2  # 1 skill + 1 snap

    snap = next(s for s in res["skills"] if s.get("is_snap"))
    assert snap["name"] == "shot1.png"
    assert snap["category"] == "Snaps"


def test_discovery_permission_error_handling(temp_dir, disk_cache, service):
    source_lib = temp_dir / "restricted"
    source_lib.mkdir()

    # Mock iterdir to raise PermissionError
    with patch.object(Path, "iterdir", side_effect=PermissionError("Denied")):
        service.sources = [str(source_lib)]

        # Should not crash
        skills = service.discover_packages_incremental(disk_cache, MagicMock(), MagicMock())
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


@patch("skill_manager.core.discovery.load_cache")
@patch("skill_manager.core.discovery.save_cache")
@patch("skill_manager.core.discovery.get_discovery_cache")
def test_discover_all_dedup_prefers_project_over_package(
    mock_get_cache, mock_save, mock_load, temp_dir, disk_cache
):
    """When a skill path is in both sources and projects, project version wins."""
    mock_get_cache.return_value.__enter__.return_value = disk_cache
    mock_load.return_value = None

    # Create a shared skill directory that would be scanned as both source and project
    shared_dir = temp_dir / "shared_skills"
    shared_dir.mkdir()
    skill_dir = shared_dir / "brainstorming"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("---\nname: Brainstorming\ncategory: Ideas\n---")

    # Also create a skill in a source-only path (to verify source skills are preserved)
    source_lib = temp_dir / "master"
    source_lib.mkdir()
    skill2 = source_lib / "unique_source_skill"
    skill2.mkdir()
    (skill2 / "SKILL.md").write_text("---\nname: Unique Source Skill\n---")

    service = DiscoveryService(
        sources=[str(source_lib), str(shared_dir)],
        projects=[str(shared_dir)],
    )

    result = service.discover_all(use_cache=False)
    state = CacheState.model_validate(result)

    # Find the brainstorming skill
    brainstorming_skills = [s for s in state.skills if s.name == "Brainstorming"]
    assert len(brainstorming_skills) == 1, "Brainstorming skill should appear exactly once"
    assert brainstorming_skills[0].is_package is False, (
        "Project version should win (is_package=False)"
    )
    assert "shared_skills" in brainstorming_skills[0].project_label, "Should have project label"

    # Verify unique source skill is still present
    unique_skills = [s for s in state.skills if s.name == "Unique Source Skill"]
    assert len(unique_skills) == 1
    assert unique_skills[0].is_package is True


@patch("skill_manager.core.discovery.load_cache")
@patch("skill_manager.core.discovery.save_cache")
@patch("skill_manager.core.discovery.get_discovery_cache")
def test_discover_all_dedup_project_only_skill(
    mock_get_cache, mock_save, mock_load, temp_dir, disk_cache
):
    """Skill only in projects has is_package=False."""
    mock_get_cache.return_value.__enter__.return_value = disk_cache
    mock_load.return_value = None

    proj_dir = temp_dir / "project"
    proj_dir.mkdir()
    skill_dir = proj_dir / "proj_skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("---\nname: Proj Skill\n---")

    service = DiscoveryService(
        sources=[],
        projects=[str(proj_dir)],
    )

    result = service.discover_all(use_cache=False)
    state = CacheState.model_validate(result)

    proj_skills = [s for s in state.skills if s.name == "Proj Skill"]
    assert len(proj_skills) == 1
    assert proj_skills[0].is_package is False
    assert "project" in proj_skills[0].project_label


@patch("skill_manager.core.discovery.load_cache")
@patch("skill_manager.core.discovery.save_cache")
@patch("skill_manager.core.discovery.get_discovery_cache")
def test_discover_all_dedup_package_only_skill(
    mock_get_cache, mock_save, mock_load, temp_dir, disk_cache
):
    """Skill only in sources has is_package=True."""
    mock_get_cache.return_value.__enter__.return_value = disk_cache
    mock_load.return_value = None

    source_lib = temp_dir / "master"
    source_lib.mkdir()
    skill_dir = source_lib / "pkg_skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("---\nname: Pkg Skill\n---")

    service = DiscoveryService(
        sources=[str(source_lib)],
        projects=[],
    )

    result = service.discover_all(use_cache=False)
    state = CacheState.model_validate(result)

    pkg_skills = [s for s in state.skills if s.name == "Pkg Skill"]
    assert len(pkg_skills) == 1
    assert pkg_skills[0].is_package is True
    assert pkg_skills[0].project_label == "Master Library"  # Package default label


# ── Post-scan path verification ─────────────────────────────────────────


class TestDiscoveryVerifiesPaths:
    """Tests that discovery removes skills with missing local_path."""

    def test_packages_verification_removes_missing(self, tmp_path: Path) -> None:
        """discover_packages_incremental removes skills whose local_path is gone."""
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("# Test Skill\n", encoding="utf-8")

        service = DiscoveryService(sources=[str(tmp_path)], projects=[])

        mock_disk_cache = MagicMock()
        mock_disk_cache.get.return_value = None

        with patch("skill_manager.core.discovery.compute_dir_fingerprint", return_value="fp1"):
            result = service.discover_packages_incremental(
                mock_disk_cache, _parse_test, _cat_test, force_full_scan=True
            )
            assert len(result) == 1
            assert result[0]["name"] == "test"

        shutil.rmtree(skill_dir)

        with patch("skill_manager.core.discovery.compute_dir_fingerprint", return_value="fp2"):
            result = service.discover_packages_incremental(
                mock_disk_cache, _parse_test, _cat_test, force_full_scan=True
            )
            assert len(result) == 0

    def test_projects_verification_removes_missing(self, tmp_path: Path) -> None:
        """discover_projects_incremental removes skills whose local_path is gone."""
        skill1 = tmp_path / "skill-a"
        skill1.mkdir()
        (skill1 / "SKILL.md").write_text("# Skill A\n", encoding="utf-8")

        skill2 = tmp_path / "skill-b"
        skill2.mkdir()
        (skill2 / "SKILL.md").write_text("# Skill B\n", encoding="utf-8")

        service = DiscoveryService(sources=[], projects=[str(tmp_path)])

        mock_disk_cache = MagicMock()
        mock_disk_cache.get.return_value = None

        with patch("skill_manager.core.discovery.compute_dir_fingerprint", return_value="fp1"):
            result = service.discover_projects_incremental(
                mock_disk_cache, _parse_by_parent, _cat_test, force_full_scan=True
            )
            assert len(result) == 1
            assert len(result[0]["skills"]) == 2

        shutil.rmtree(skill1)

        with patch("skill_manager.core.discovery.compute_dir_fingerprint", return_value="fp2"):
            result = service.discover_projects_incremental(
                mock_disk_cache, _parse_by_parent, _cat_test, force_full_scan=True
            )
            assert len(result) == 1
            assert len(result[0]["skills"]) == 1
            assert result[0]["skills"][0]["name"] == "skill-b"

    def test_verification_keeps_existing_skills(self, tmp_path: Path) -> None:
        """Verification only removes missing skills, keeps existing ones."""
        skill1 = tmp_path / "skill-1"
        skill1.mkdir()
        (skill1 / "SKILL.md").write_text("# Skill 1\n", encoding="utf-8")

        skill2 = tmp_path / "skill-2"
        skill2.mkdir()
        (skill2 / "SKILL.md").write_text("# Skill 2\n", encoding="utf-8")

        service = DiscoveryService(sources=[str(tmp_path)], projects=[])

        mock_disk_cache = MagicMock()
        mock_disk_cache.get.return_value = None

        with patch("skill_manager.core.discovery.compute_dir_fingerprint", return_value="fp1"):
            result = service.discover_packages_incremental(
                mock_disk_cache, _parse_by_parent, _cat_test, force_full_scan=True
            )
            assert len(result) == 2

        shutil.rmtree(skill1)

        with patch("skill_manager.core.discovery.compute_dir_fingerprint", return_value="fp2"):
            result = service.discover_packages_incremental(
                mock_disk_cache, _parse_by_parent, _cat_test, force_full_scan=True
            )
            assert len(result) == 1
            assert result[0]["name"] == "skill-2"


# ── force_full_scan parameter ───────────────────────────────────────────


class TestForceFullScan:
    """Tests that force_full_scan bypasses diskcache fingerprint checks."""

    def test_discover_projects_incremental_force_skips_cache(self, tmp_path: Path) -> None:
        """When force_full_scan=True, diskcache fingerprint is not checked."""
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("# Test Skill\n", encoding="utf-8")

        service = DiscoveryService(sources=[], projects=[str(tmp_path)])
        mock_disk_cache = MagicMock()

        with patch("skill_manager.core.discovery.compute_dir_fingerprint", return_value="fp1"):
            service.discover_projects_incremental(
                mock_disk_cache, _parse_skill, _cat_test, force_full_scan=True
            )
            mock_disk_cache.get.assert_not_called()

    def test_discover_projects_incremental_no_force_checks_cache(self, tmp_path: Path) -> None:
        """When force_full_scan=False, diskcache fingerprint IS checked."""
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("# Test Skill\n", encoding="utf-8")

        service = DiscoveryService(sources=[], projects=[str(tmp_path)])

        cached_project_data = {
            "project_path": str(tmp_path),
            "project_root": str(tmp_path),
            "project_label": "test",
            "skills": [{"name": "cached", "local_path": str(skill_dir)}],
        }
        mock_disk_cache = MagicMock()

        def mock_get(key):
            key_str = str(key)
            if "proj_skills:" in key_str:
                return cached_project_data
            if "dir_fp:" in key_str:
                return "cached-fp"
            return None

        mock_disk_cache.get.side_effect = mock_get

        with patch(
            "skill_manager.core.discovery.compute_dir_fingerprint", return_value="cached-fp"
        ):
            result = service.discover_projects_incremental(
                mock_disk_cache, _parse_skill, _cat_test, force_full_scan=False
            )
            assert mock_disk_cache.get.called
            assert result[0]["skills"][0]["name"] == "cached"

    def test_discover_packages_incremental_force_skips_cache(self, tmp_path: Path) -> None:
        """When force_full_scan=True, package diskcache fingerprint is not checked."""
        skill_dir = tmp_path / "pkg-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("# Pkg Skill\n", encoding="utf-8")

        service = DiscoveryService(sources=[str(tmp_path)], projects=[])
        mock_disk_cache = MagicMock()

        with patch(
            "skill_manager.core.discovery.compute_dir_fingerprint", return_value="cached-fp"
        ):
            service.discover_packages_incremental(
                mock_disk_cache, _parse_skill_pkg, _cat_pkg, force_full_scan=True
            )
            mock_disk_cache.get.assert_not_called()

    def test_discover_packages_incremental_no_force_checks_cache(self, tmp_path: Path) -> None:
        """When force_full_scan=False, package diskcache fingerprint IS checked."""
        skill_dir = tmp_path / "pkg-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("# Pkg Skill\n", encoding="utf-8")

        service = DiscoveryService(sources=[str(tmp_path)], projects=[])

        cached_skills = [{"name": "cached-pkg", "local_path": str(skill_dir)}]
        mock_disk_cache = MagicMock()

        def mock_get(key):
            key_str = str(key)
            if "pkg_skills:" in key_str:
                return cached_skills
            if "dir_fp:" in key_str:
                return "cached-fp"
            return None

        mock_disk_cache.get.side_effect = mock_get

        with patch(
            "skill_manager.core.discovery.compute_dir_fingerprint", return_value="cached-fp"
        ):
            result = service.discover_packages_incremental(
                mock_disk_cache, _parse_skill_pkg, _cat_pkg, force_full_scan=False
            )
            assert mock_disk_cache.get.called
            assert result[0]["name"] == "cached-pkg"

    def test_refresh_skills_passes_force_to_load(self) -> None:
        """AppController.refreshSkills forwards force_full_scan to loadInitialData."""
        from skill_manager.app import AppController

        app = MagicMock(spec=AppController)
        app.discovery = MagicMock()

        AppController.refreshSkills(app, "test", True)

        app.discovery.cancel_inflight.assert_called_once()
        app.discovery.loadInitialData.assert_called_once_with(force_full_scan=True, silent=True)


# ── DiscoveryController SDET contract ───────────────────────────────────


class TestDiscoveryControllerSDET:
    def test_load_initial_data_triggers_task(self, controller, sdet_app):
        controller.loadInitialData()
        assert sdet_app.task_runner.run.call_count == 2

    @patch("skill_manager.controllers.discovery_controller.DiscoveryService")
    def test_discover_all_background_success(self, mock_service_class, controller, sdet_app):
        mock_service = mock_service_class.return_value
        mock_result = {
            "skills": [{"name": "Skill 1", "local_path": "/path/1", "is_package": True}],
            "projects": [],
            "categories": ["Cat 1"],
            "status": "Done",
        }
        mock_service.discover_all.return_value = mock_result

        result = controller._discover_all_background(mock_service, False)

        assert isinstance(result, dict)
        assert len(result["skills"]) == 1
        assert result["skills"][0]["name"] == "Skill 1"
        assert result["categories"] == ["Cat 1"]

    def test_commit_prepared_state_full_set(self, controller, sdet_app):
        skill = Skill(name="Skill 1", local_path="/path/1", is_package=True, main_category="")
        state = PreparedModelState(
            all_skills=[skill],
            search_engine=MagicMock(),
            all_filtered_skills=[skill],
            visible_rows=[skill],
            categories=["Cat 1"],
            status="Ready",
            generation=0,
            is_final=True,
        )

        controller._commit_prepared_state(state)

        sdet_app._library_model.replacePreparedState.assert_called_once()
        sdet_app._quick_copy_model.replacePreparedState.assert_called_once()
        assert sdet_app._categories == ["Cat 1"]
        sdet_app._set_status.assert_called_with("Ready")

    def test_handle_loading_error(self, controller, sdet_app):
        controller._handle_loading_error("Fail")
        sdet_app._set_status.assert_called_with("Fail")

    def test_cancellation_supersedes_result(self, controller, sdet_app):
        """After incrementing generation, in-flight results are dropped."""
        controller._refresh_generation = 0
        skill = Skill(name="S1", local_path="/p1", is_package=True, main_category="")
        state = PreparedModelState(
            all_skills=[skill],
            search_engine=MagicMock(),
            all_filtered_skills=[skill],
            visible_rows=[skill],
            categories=[],
            status="Done",
            generation=0,
            is_final=True,
        )
        controller._commit_prepared_state(state)
        sdet_app._library_model.replacePreparedState.assert_called_once()

        # Now supersede
        sdet_app._library_model.replacePreparedState.reset_mock()
        controller._refresh_generation = 1  # Simulate cancellation
        state.generation = 0  # Old generation
        controller._commit_prepared_state(state)
        sdet_app._library_model.replacePreparedState.assert_not_called()
