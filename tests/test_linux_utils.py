"""Tests for ``skill_manager.utils.linux``.

These tests focus on correctness of logic (tool selection, fallback
ordering) without actually calling system tools.  All external
subprocess calls are mocked.
"""

from unittest.mock import MagicMock, patch

from skill_manager.utils import linux


def test_set_clipboard_wl_copy_success():
    with (
        patch("skill_manager.utils.linux._has_wl_copy", return_value=True),
        patch("skill_manager.utils.linux.subprocess.run") as mock_run,
    ):
        mock_run.return_value = MagicMock(returncode=0)
        assert linux.set_clipboard("hello") is True
        mock_run.assert_called_once()


def test_set_clipboard_all_fail():
    with (
        patch("skill_manager.utils.linux._has_wl_copy", return_value=False),
        patch("skill_manager.utils.linux._has_pyperclip", return_value=False),
    ):
        assert linux.set_clipboard("hello") is False


def test_get_clipboard_wl_paste_success():
    with (
        patch("skill_manager.utils.linux._has_wl_paste", return_value=True),
        patch("skill_manager.utils.linux.subprocess.run") as mock_run,
    ):
        mock_run.return_value = MagicMock(returncode=0, stdout="hello")
        assert linux.get_clipboard() == "hello"


def test_send_ctrl_v_ydotool():
    with (
        patch("skill_manager.utils.linux.injection_allowed", return_value=True),
        patch("skill_manager.utils.linux._has_ydotool", return_value=True),
        patch("skill_manager.utils.linux.subprocess.run") as mock_run,
    ):
        assert linux.send_ctrl_v() is True
        mock_run.assert_called_once()


def test_send_ctrl_v_all_fail():
    with (
        patch("skill_manager.utils.linux.injection_allowed", return_value=True),
        patch("skill_manager.utils.linux._has_ydotool", return_value=False),
        patch.dict("sys.modules", {"pyautogui": None}),
    ):
        assert linux.send_ctrl_v() is False


def test_send_ctrl_v_blocked_under_pytest():
    """Injection guard: real keystrokes must never reach the live desktop
    when running under pytest (regression: ydotool was invoked for real).
    """
    with (
        patch("skill_manager.utils.linux._has_ydotool", return_value=True),
        patch("skill_manager.utils.linux.subprocess.run") as mock_run,
    ):
        assert linux.send_ctrl_v() is False
        mock_run.assert_not_called()


def test_find_window_by_title_xdotool():
    with (
        patch("skill_manager.utils.linux.shutil.which", return_value="/usr/bin/xdotool"),
        patch("skill_manager.utils.linux.subprocess.run") as mock_run,
    ):
        mock_run.return_value = MagicMock(returncode=0, stdout="12345\n")
        result = linux.find_window_by_title("Skill Manager")
        assert result == 12345


def test_find_window_by_title_wayland_fallback():
    with (
        patch("skill_manager.utils.linux.shutil.which", return_value=None),
        patch("skill_manager.utils.linux.os.environ.get", return_value="wayland"),
    ):
        result = linux.find_window_by_title("Skill Manager")
        assert result == 0


def test_find_window_by_title_not_found():
    with (
        patch("skill_manager.utils.linux.shutil.which", return_value=None),
        patch("skill_manager.utils.linux.os.environ.get", return_value=None),
    ):
        result = linux.find_window_by_title("Skill Manager")
        assert result is None


def test_send_paste_to_focused_window_delegates():
    with patch("skill_manager.utils.linux.send_ctrl_v", return_value=True) as mock_fn:
        assert linux.send_paste_to_focused_window() is True
        mock_fn.assert_called_once()


def test_move_mouse_no_tools():
    with (
        patch("skill_manager.utils.linux.injection_allowed", return_value=True),
        patch("skill_manager.utils.linux.shutil.which", return_value=None),
        patch.dict("sys.modules", {"pyautogui": None}),
    ):
        assert linux.move_mouse(100, 200) is False


def test_type_text_no_tools():
    with (
        patch("skill_manager.utils.linux.injection_allowed", return_value=True),
        patch("skill_manager.utils.linux.shutil.which", return_value=None),
        patch.dict("sys.modules", {"pyautogui": None}),
    ):
        assert linux.type_text("hello") == 0


def test_input_injection_blocked_offscreen():
    """Injection guard: offscreen/headless runs must not inject input."""
    with (
        patch("skill_manager.utils.linux.os.environ.get", return_value="offscreen"),
        patch("skill_manager.utils.linux.subprocess.run") as mock_run,
    ):
        assert linux.move_mouse(100, 200) is False
        assert linux.click_mouse(100, 200) is False
        assert linux.type_text("hello") == 0
        assert linux.send_ctrl_v() is False
        mock_run.assert_not_called()


# ---------------------------------------------------------------------------
# capture_screen (delegates to portal/gnome-screenshot on Wayland)
# ---------------------------------------------------------------------------


def test_capture_screen_all_strategies_fail():
    with (
        patch(
            "skill_manager.controllers.screenshot_controller._portal_capture",
            return_value=None,
        ),
        patch(
            "skill_manager.controllers.screenshot_controller._gnome_screenshot_capture",
            return_value=None,
        ),
    ):
        assert linux.capture_screen() is None
        assert linux.capture_screen("/tmp/x.png") is None


def test_capture_screen_portal_succeeds():
    with patch(
        "skill_manager.controllers.screenshot_controller._portal_capture",
        return_value="/tmp/portal_test.png",
    ):
        result = linux.capture_screen()
        assert result == "/tmp/portal_test.png"
