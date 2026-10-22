"""Safety guards for the MCP automation surface.

Covers the defects found while auditing the bridge:

* the input guard failed **open** on Wayland (the "cannot locate the
  window" sentinel was treated as "found"), so MCP input tools could
  inject into whatever window the user had focused;
* ``sm_lint`` could rewrite the source tree (``ruff --fix``) even in
  read-only mode;
* the write tools could reach outside the configured sources/projects
  (path traversal, arbitrary paths, a symlink escape);
* the delete path checked the AGENTS.md exclusion *after* deleting.
"""

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from skill_manager.mcp.bridge._guard import (
    is_excluded,
    is_within,
    project_roots,
    safe_skill_name,
    skill_source_roots,
)
from skill_manager.utils.input_guard import gui_window_present


def _run(coro):
    """Drive a coroutine to completion without an async plugin."""
    import anyio

    return anyio.run(lambda: coro)


# ── B6: the input guard must fail closed ─────────────────────────────────

#: The Wayland sentinel is a Linux/X11 concept; Windows uses FindWindowW.
_LINUX_GUI = sys.platform != "win32"


@pytest.mark.skipif(not _LINUX_GUI, reason="the Wayland sentinel is an X11/Wayland path")
def test_gui_window_present_rejects_the_wayland_unknown_sentinel():
    """The "cannot locate the window" sentinel must count as absent.

    On pure Wayland the window cannot be found, so the guard has to
    refuse: injecting blind would type into an unrelated window.
    """
    from skill_manager.utils.linux import WINDOW_ID_UNKNOWN

    with patch(
        "skill_manager.utils.linux.find_window_by_title",
        return_value=WINDOW_ID_UNKNOWN,
    ):
        assert gui_window_present() is False


@pytest.mark.skipif(not _LINUX_GUI, reason="the X11/Wayland path")
def test_gui_window_present_accepts_a_real_window_id():
    with patch("skill_manager.utils.linux.find_window_by_title", return_value=4242):
        assert gui_window_present() is True


@pytest.mark.skipif(not _LINUX_GUI, reason="the X11/Wayland path")
def test_gui_window_present_rejects_a_missing_window():
    with patch("skill_manager.utils.linux.find_window_by_title", return_value=None):
        assert gui_window_present() is False


@pytest.mark.skipif(not _LINUX_GUI, reason="the X11/Wayland path")
def test_input_refused_reason_when_the_window_cannot_be_located():
    from skill_manager.utils.linux import WINDOW_ID_UNKNOWN

    with patch(
        "skill_manager.utils.linux.find_window_by_title",
        return_value=WINDOW_ID_UNKNOWN,
    ):
        from skill_manager.utils.input_guard import injection_refused_reason

        # Under pytest the first refusal reason wins, so the window check
        # is exercised on its own here.
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("PYTEST_CURRENT_TEST", None)
            os.environ.pop("QT_QPA_PLATFORM", None)
            reason = injection_refused_reason()
        assert reason is not None
        assert "window not running" in reason


@pytest.mark.skipif(sys.platform != "win32", reason="the Windows FindWindowW path")
def test_gui_window_present_on_windows_requires_a_live_hwnd():
    """On Windows the guard needs a real HWND from ``FindWindowW``."""
    with patch("ctypes.windll.user32.FindWindowW", return_value=0):
        assert gui_window_present() is False
    with patch("ctypes.windll.user32.FindWindowW", return_value=1234):
        assert gui_window_present() is True


# ── guard helpers ────────────────────────────────────────────────────────


def test_safe_skill_name_rejects_traversal():
    assert safe_skill_name("../../evil") is None
    assert safe_skill_name("a/b") is None
    assert safe_skill_name("a\\b") is None
    assert safe_skill_name("..") is None
    assert safe_skill_name(".") is None
    assert safe_skill_name("") is None
    assert safe_skill_name("   ") is None


def test_safe_skill_name_rejects_absolute_paths():
    assert safe_skill_name("/etc/passwd") is None
    assert safe_skill_name("C:\\Windows") is None


def test_safe_skill_name_accepts_a_plain_name():
    assert safe_skill_name("my-skill") == "my-skill"
    assert safe_skill_name("  my_skill  ") == "my_skill"


def test_is_within_accepts_children_and_rejects_outsiders(tmp_path):
    root = tmp_path / "source"
    root.mkdir()
    child = root / "skill"
    child.mkdir()

    assert is_within(child, [root]) is True
    assert is_within(root, [root]) is True
    assert is_within(tmp_path / "elsewhere", [root]) is False
    assert is_within("/etc", [root]) is False


def test_is_within_resolves_symlinks(tmp_path):
    """A symlink that points outside the root must not pass."""
    root = tmp_path / "source"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    link = root / "escape"
    try:
        link.symlink_to(outside)
    except OSError as exc:
        # Creating a symlink needs extra privileges on Windows.
        pytest.skip(f"symlinks are not available here: {exc}")

    assert is_within(link / "file.txt", [root]) is False


def test_is_within_with_no_roots_is_false(tmp_path):
    assert is_within(tmp_path, []) is False


def test_is_excluded_matches_the_agents_md_markers():
    assert is_excluded("/repo/.agents/skills/x") is True
    assert is_excluded("/repo/.agents\\commands\\x.md") is True
    assert is_excluded("/repo/TODO.md") is True
    assert is_excluded("/repo/src/skill.md") is False


def test_roots_come_from_the_controller():
    controller = MagicMock()
    controller._sources = ["/a", "/b"]
    controller._projects = ["/p"]
    assert [str(p) for p in skill_source_roots(controller)] == [
        str(Path("/a")),
        str(Path("/b")),
    ]
    assert [str(p) for p in project_roots(controller)] == [str(Path("/p"))]


# ── B9: sm_lint --fix must be write-gated ────────────────────────────────


def test_sm_lint_fix_requires_write_mode():
    from skill_manager.mcp.tools.build import get_handlers

    handlers = get_handlers(allow_write=False)
    result = handlers["sm_lint"]({"path": "src", "fix": True})
    assert result.ok is False
    assert "write mode disabled" in (result.error or "")


def test_sm_lint_without_fix_is_allowed_in_read_only_mode():
    from skill_manager.mcp.tools.build import get_handlers

    handlers = get_handlers(allow_write=False)
    with patch("skill_manager.mcp.tools.build.run_lint") as mock_lint:
        mock_lint.return_value = {"passed": True, "returncode": 0}
        result = handlers["sm_lint"]({"path": "src", "fix": False})
    assert result.ok is True
    mock_lint.assert_called_once_with(path="src", fix=False)


def test_sm_lint_fix_runs_in_write_mode():
    from skill_manager.mcp.tools.build import get_handlers

    handlers = get_handlers(allow_write=True)
    with patch("skill_manager.mcp.tools.build.run_lint") as mock_lint:
        mock_lint.return_value = {"passed": True, "returncode": 0}
        result = handlers["sm_lint"]({"path": "src", "fix": True})
    assert result.ok is True
    mock_lint.assert_called_once_with(path="src", fix=True)


# ── B10: the write tools must stay inside the configured roots ─────────


def _controller_with_source(tmp_path):
    controller = MagicMock()
    source = tmp_path / "source"
    source.mkdir()
    controller._sources = [str(source)]
    controller._projects = []
    return controller, source


def test_create_skill_refuses_a_traversing_name(tmp_path):
    from skill_manager.mcp.bridge._skills import create_skill

    controller, source = _controller_with_source(tmp_path)
    with (
        patch("skill_manager.mcp.bridge._skills._controller_or_none", return_value=controller),
        pytest.raises(ValueError, match="not a valid folder name"),
    ):
        _run(create_skill(name="../../evil", content="x"))

    assert not (tmp_path / "evil").exists()


def test_create_skill_refuses_a_parent_outside_the_sources(tmp_path):
    from skill_manager.mcp.bridge._skills import create_skill

    controller, source = _controller_with_source(tmp_path)
    outside = tmp_path / "outside"
    with (
        patch("skill_manager.mcp.bridge._skills._controller_or_none", return_value=controller),
        pytest.raises(ValueError, match="outside the configured sources"),
    ):
        _run(create_skill(name="skill", content="x", source_path=str(outside)))

    assert not (outside / "skill").exists()


def test_create_skill_writes_inside_a_configured_source(tmp_path):
    from skill_manager.mcp.bridge._skills import create_skill

    controller, source = _controller_with_source(tmp_path)
    with (
        patch("skill_manager.mcp.bridge._skills._controller_or_none", return_value=controller),
        patch("skill_manager.mcp.bridge._skills.sync_skills"),
    ):
        result = _run(create_skill(name="my-skill", content="# hi"))

    assert (source / "my-skill" / "SKILL.md").exists()
    assert result["created"] is True


def test_update_skill_refuses_an_unknown_path(tmp_path):
    from skill_manager.mcp.bridge._skills import update_skill

    controller, _source = _controller_with_source(tmp_path)
    controller._library_model._all_skills = []
    stray = tmp_path / "stray.md"
    stray.write_text("x", encoding="utf-8")

    with (
        patch("skill_manager.mcp.bridge._skills._controller_or_none", return_value=controller),
        pytest.raises(ValueError, match="refusing to guess a write target"),
    ):
        _run(update_skill(skill_id=str(stray), content="y"))

    assert stray.read_text(encoding="utf-8") == "x"


def test_update_skill_refuses_an_excluded_path(tmp_path):
    from skill_manager.mcp.bridge._skills import update_skill

    controller, source = _controller_with_source(tmp_path)
    excluded = source / ".agents" / "skills" / "x"
    excluded.mkdir(parents=True)
    (excluded / "SKILL.md").write_text("original", encoding="utf-8")
    controller._library_model._all_skills = [MagicMock(name="x", local_path=str(excluded))]

    with (
        patch("skill_manager.mcp.bridge._skills._controller_or_none", return_value=controller),
        pytest.raises(ValueError, match="excluded path"),
    ):
        _run(update_skill(skill_id=str(excluded), content="overwritten"))

    assert (excluded / "SKILL.md").read_text(encoding="utf-8") == "original"


def test_delete_skill_refuses_an_unknown_path(tmp_path):
    from skill_manager.mcp.bridge._skills import delete_skill

    controller, _source = _controller_with_source(tmp_path)
    controller._library_model._all_skills = []
    stray = tmp_path / "stray.md"
    stray.write_text("x", encoding="utf-8")

    with (
        patch("skill_manager.mcp.bridge._skills._controller_or_none", return_value=controller),
        pytest.raises(ValueError, match="refusing to guess a deletion target"),
    ):
        _run(delete_skill(skill_id=str(stray)))

    assert stray.exists()


def test_deploy_refuses_an_unknown_target(tmp_path):
    from skill_manager.mcp.bridge._skills import deploy

    controller, source = _controller_with_source(tmp_path)
    controller._library_model._all_skills = [
        MagicMock(name="x", local_path=str(source / "x"), is_package=False)
    ]
    stray = tmp_path / "stray-target"
    stray.mkdir()

    with (
        patch("skill_manager.mcp.bridge._skills._controller_or_none", return_value=controller),
        pytest.raises(ValueError, match="refusing to deploy to an arbitrary directory"),
    ):
        _run(deploy(skill_id="x", target=str(stray)))

    assert not (stray / ".agents").exists()


def test_delete_tool_checks_the_exclusion_before_deleting(tmp_path):
    """The AGENTS.md exclusion is evaluated before anything is removed."""
    from skill_manager.mcp.tools.write import get_handlers

    handlers = get_handlers(allow_write=True)
    with patch("skill_manager.mcp.tools.write.delete_skill") as mock_delete:
        result = _run(handlers["sm_delete_skill"]({"skill_id": "/repo/.agents/skills/x"}))
    assert result.ok is False
    mock_delete.assert_not_called()


# ── The MCP read path must not block the event loop ─────────────────────


def test_sync_skills_scans_off_the_event_loop(monkeypatch, tmp_path):
    """The discovery scan must not run on the MCP event-loop thread.

    It used to run inline, so a full scan stalled every other MCP request
    for its whole duration.  The scan now runs on a worker thread and only
    the model update happens on the calling thread.
    """
    import threading

    from skill_manager.mcp.bridge import _skills as skills_mod

    controller = MagicMock()
    controller._sources = []
    controller._projects = []
    controller._library_model._all_skills = []

    scan_thread: dict = {}

    def fake_scan(_controller, force_full_scan=False):  # noqa: ARG001
        scan_thread["id"] = threading.get_ident()
        return []

    monkeypatch.setattr(skills_mod, "_scan_sources", fake_scan)

    async def _drive():
        return await skills_mod.sync_skills()

    import anyio

    caller_thread = threading.get_ident()
    result = anyio.run(_drive)

    assert result["synced"] is True
    assert scan_thread["id"] != caller_thread
