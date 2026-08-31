"""Tests for snap refresh fix: fingerprint includes screenshots and watcher handles images."""

import time
from pathlib import Path

from skill_manager.core.discovery import (
    _snap_fingerprint,
    compute_dir_fingerprint,
)
from skill_manager.core.file_watch import SkillFolderEventHandler, SkillFolderWatcher


def test_snap_fingerprint_changes_on_png_add(tmp_path: Path):
    proj = tmp_path / "proj"
    proj.mkdir()
    agents = proj / ".agents"
    agents.mkdir()
    snap_dir = agents / "screenshots"
    snap_dir.mkdir()

    fp_before = compute_dir_fingerprint(proj)
    assert fp_before != ""

    # Direct helper check
    snap_before = _snap_fingerprint(proj)
    assert snap_before[0] == 0

    (snap_dir / "Screenshot_20260101_120000.png").write_bytes(b"fake png")
    time.sleep(0.05)

    snap_after = _snap_fingerprint(proj)
    assert snap_after[0] == 1
    assert snap_after != snap_before

    fp_after = compute_dir_fingerprint(proj)
    assert fp_before != fp_after, "Fingerprint must change when a screenshot is added"


def test_snap_fingerprint_changes_on_png_delete(tmp_path: Path):
    proj = tmp_path / "proj2"
    proj.mkdir()
    snap_dir = proj / ".agents" / "screenshots"
    snap_dir.mkdir(parents=True)
    img = snap_dir / "a.png"
    img.write_bytes(b"x")
    fp_before = compute_dir_fingerprint(proj)

    img.unlink()
    time.sleep(0.05)
    fp_after = compute_dir_fingerprint(proj)
    assert fp_before != fp_after


def test_snap_fingerprint_ignores_non_image(tmp_path: Path):
    proj = tmp_path / "proj3"
    proj.mkdir()
    snap_dir = proj / ".agents" / "screenshots"
    snap_dir.mkdir(parents=True)
    fp_before = compute_dir_fingerprint(proj)
    (snap_dir / "readme.txt").write_text("hello")
    fp_after = compute_dir_fingerprint(proj)
    # txt file should not affect snap count, fingerprint should stay same
    assert fp_before == fp_after


def test_commands_fingerprint_changes(tmp_path: Path):
    proj = tmp_path / "proj4"
    proj.mkdir()
    cmd_dir = proj / ".agents" / "commands"
    cmd_dir.mkdir(parents=True)
    fp_before = compute_dir_fingerprint(proj)
    (cmd_dir / "hello.md").write_text("# hello")
    fp_after = compute_dir_fingerprint(proj)
    assert fp_before != fp_after


def test_watcher_handles_png_events(tmp_path: Path):
    # Ensure _is_relevant_path allows screenshots and on_any_event handles png
    handler = SkillFolderEventHandler(callback=lambda p: None, debounce_ms=0)
    # Should be relevant
    assert handler._is_relevant_path(str(tmp_path / ".agents" / "screenshots" / "a.png"))
    # Simulate event via on_any_event - should fire for png
    fired = []
    handler2 = SkillFolderEventHandler(callback=lambda p: fired.append(p), debounce_ms=0)

    class FakeEvent:
        def __init__(self, src, is_dir=False):
            self.src_path = src
            self.is_directory = is_dir
            self.dest_path = ""

    png_path = str(tmp_path / ".agents" / "screenshots" / "img.png")
    handler2.on_any_event(FakeEvent(png_path, is_dir=False))
    assert len(fired) == 1

    # md also fires
    fired.clear()
    md_path = str(tmp_path / ".agents" / "commands" / "cmd.md")
    handler2.on_any_event(FakeEvent(md_path, is_dir=False))
    assert len(fired) == 1

    # txt should not fire
    fired.clear()
    txt_path = str(tmp_path / ".agents" / "screenshots" / "readme.txt")
    handler2.on_any_event(FakeEvent(txt_path, is_dir=False))
    assert len(fired) == 0


def test_watcher_expand_includes_screenshots(tmp_path: Path):
    proj = tmp_path / "proj5"
    proj.mkdir()
    agents = proj / ".agents"
    agents.mkdir()
    (agents / "skills").mkdir()
    (agents / "screenshots").mkdir()
    expanded = SkillFolderWatcher._expand_watch_paths([str(proj)])
    expanded_strs = [str(p) for p in expanded]
    assert str(agents) in expanded_strs
    assert str(agents / "skills") in expanded_strs
    assert str(agents / "screenshots") in expanded_strs


def test_watcher_expand_always_watches_agents(tmp_path: Path):
    proj = tmp_path / "proj6"
    proj.mkdir()
    agents = proj / ".agents"
    agents.mkdir()
    (agents / "skills").mkdir()
    # no screenshots yet
    expanded = SkillFolderWatcher._expand_watch_paths([str(proj)])
    expanded_strs = [str(p) for p in expanded]
    assert str(agents) in expanded_strs


def test_discovery_includes_manual_screenshot(tmp_path: Path):
    from skill_manager.core.discovery import DiscoveryService, get_discovery_cache

    proj = tmp_path / "myproj"
    proj.mkdir()
    # minimal skill to make project discoverable (skill must be direct child with SKILL.md)
    # but discovery for projects scans direct children of project root, so create skill
    skill = proj / "my_skill"
    skill.mkdir()
    (skill / "SKILL.md").write_text("# Test\n")
    # create screenshot manually
    snap_dir = proj / ".agents" / "screenshots"
    snap_dir.mkdir(parents=True)
    (snap_dir / "manual.png").write_bytes(b"pngdata")

    service = DiscoveryService(sources=[], projects=[str(proj)])
    result = service.discover_all(use_cache=False, force_full_scan=True)
    skills = result.get("skills", [])
    snap_skills = [s for s in skills if s.get("is_snap")]
    assert len(snap_skills) == 1
    assert snap_skills[0].get("local_path", "").endswith("manual.png")

    # Incremental fingerprint should include snap: test cache hit then add new snap and rescan with force_full_scan=False
    with get_discovery_cache() as cache:
        cache.clear()
    # First incremental should populate cache
    service2 = DiscoveryService(sources=[], projects=[str(proj)])
    with get_discovery_cache() as cache:
        service2.discover_projects_incremental(
            cache,
            service2._wrap_parse_skill_md(cache),
            service2._wrap_categorize_skill(cache),
            force_full_scan=True,
        )
    # Now add another screenshot
    (snap_dir / "manual2.jpg").write_bytes(b"jpgdata")
    time.sleep(0.05)
    # fingerprint should differ, so next incremental scan without force should detect new file
    # We test via full discover_all with incremental false (should rescan due to fingerprint change)
    service3 = DiscoveryService(sources=[], projects=[str(proj)])
    result2 = service3.discover_all(use_cache=False, force_full_scan=False)
    snap_skills2 = [s for s in result2.get("skills", []) if s.get("is_snap")]
    assert len(snap_skills2) == 2, f"Expected 2 snaps after incremental, got {snap_skills2}"
