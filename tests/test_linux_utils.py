"""Tests for ``skill_manager.utils.linux``.

These tests focus on correctness of logic (tool selection, fallback
ordering, environment sanitization) without actually calling system tools.
All external subprocess calls are mocked.
"""

import os
import subprocess
import sys
from unittest.mock import ANY, MagicMock, patch

from skill_manager.utils import linux


def test_get_clean_env_strips_ld_library_path():
    with patch.dict(
        linux.os.environ, {"LD_LIBRARY_PATH": "/opt/app/_internal", "FOO": "BAR"}, clear=True
    ):
        clean = linux.get_clean_env()
        assert "LD_LIBRARY_PATH" not in clean
        assert clean["FOO"] == "BAR"


def test_get_clean_env_restores_ld_library_path_orig():
    with patch.dict(
        linux.os.environ,
        {"LD_LIBRARY_PATH": "/opt/app/_internal", "LD_LIBRARY_PATH_ORIG": "/usr/lib/custom"},
        clear=True,
    ):
        clean = linux.get_clean_env()
        assert clean["LD_LIBRARY_PATH"] == "/usr/lib/custom"


def test_find_system_binary_via_which():
    with patch("skill_manager.utils.linux.shutil.which", return_value="/usr/bin/wl-copy"):
        assert linux.find_system_binary("wl-copy") == "/usr/bin/wl-copy"


def test_find_system_binary_via_fallback_dir():
    expected = os.path.normpath("/usr/bin/wl-copy")
    with (
        patch("skill_manager.utils.linux.shutil.which", return_value=None),
        patch(
            "skill_manager.utils.linux.os.path.isfile",
            side_effect=lambda p: os.path.normpath(p) == expected,
        ),
        patch("skill_manager.utils.linux.os.access", return_value=True),
    ):
        result = linux.find_system_binary("wl-copy")
        assert result is not None
        assert os.path.normpath(result) == expected


def test_is_wayland_active_session_type():
    with patch.dict(linux.os.environ, {"XDG_SESSION_TYPE": "wayland"}, clear=True):
        assert linux.is_wayland_active() is True


def test_is_wayland_active_display():
    with patch.dict(linux.os.environ, {"WAYLAND_DISPLAY": "wayland-0"}, clear=True):
        assert linux.is_wayland_active() is True


def test_is_wayland_active_socket_in_runtime_dir():
    with (
        patch.dict(linux.os.environ, {"XDG_RUNTIME_DIR": "/run/user/1000"}, clear=True),
        patch("skill_manager.utils.linux.os.path.isdir", return_value=True),
        patch("skill_manager.utils.linux.os.listdir", return_value=["wayland-0", "bus"]),
    ):
        assert linux.is_wayland_active() is True


def test_set_clipboard_wl_copy_success():
    with (
        patch(
            "skill_manager.utils.linux.find_system_binary",
            side_effect=lambda name: "/usr/bin/wl-copy" if name == "wl-copy" else None,
        ),
        patch("skill_manager.utils.linux.is_wayland_active", return_value=True),
        patch("skill_manager.utils.linux.subprocess.run") as mock_run,
    ):
        mock_run.return_value = MagicMock(returncode=0)
        assert linux.set_clipboard("hello") is True
        mock_run.assert_called_once_with(
            ["/usr/bin/wl-copy"],
            input="hello",
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=5,
            env=ANY,
        )


def test_set_clipboard_xclip_success():
    with (
        patch(
            "skill_manager.utils.linux.find_system_binary",
            side_effect=lambda name: "/usr/bin/xclip" if name == "xclip" else None,
        ),
        patch("skill_manager.utils.linux.is_wayland_active", return_value=False),
        patch("skill_manager.utils.linux.subprocess.run") as mock_run,
    ):
        mock_run.return_value = MagicMock(returncode=0)
        assert linux.set_clipboard("hello_xclip") is True
        mock_run.assert_called_once_with(
            ["/usr/bin/xclip", "-selection", "clipboard"],
            input="hello_xclip",
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=5,
            env=ANY,
        )


def test_set_clipboard_xsel_success():
    with (
        patch(
            "skill_manager.utils.linux.find_system_binary",
            side_effect=lambda name: "/usr/bin/xsel" if name == "xsel" else None,
        ),
        patch("skill_manager.utils.linux.is_wayland_active", return_value=False),
        patch("skill_manager.utils.linux.subprocess.run") as mock_run,
    ):
        mock_run.return_value = MagicMock(returncode=0)
        assert linux.set_clipboard("hello_xsel") is True
        mock_run.assert_called_once_with(
            ["/usr/bin/xsel", "--clipboard", "--input"],
            input="hello_xsel",
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=5,
            env=ANY,
        )


def test_set_clipboard_all_fail():
    with (
        patch("skill_manager.utils.linux.find_system_binary", return_value=None),
        patch("skill_manager.utils.linux.is_wayland_active", return_value=False),
        patch("skill_manager.utils.linux._has_pyperclip", return_value=False),
    ):
        assert linux.set_clipboard("hello") is False


def test_get_clipboard_wl_paste_success():
    with (
        patch(
            "skill_manager.utils.linux.find_system_binary",
            side_effect=lambda name: "/usr/bin/wl-paste" if name == "wl-paste" else None,
        ),
        patch("skill_manager.utils.linux.is_wayland_active", return_value=True),
        patch("skill_manager.utils.linux.subprocess.run") as mock_run,
    ):
        mock_run.return_value = MagicMock(returncode=0, stdout="hello")
        assert linux.get_clipboard() == "hello"


def test_get_clipboard_xclip_success():
    with (
        patch(
            "skill_manager.utils.linux.find_system_binary",
            side_effect=lambda name: "/usr/bin/xclip" if name == "xclip" else None,
        ),
        patch("skill_manager.utils.linux.is_wayland_active", return_value=False),
        patch("skill_manager.utils.linux.subprocess.run") as mock_run,
    ):
        mock_run.return_value = MagicMock(returncode=0, stdout="hello_xclip")
        assert linux.get_clipboard() == "hello_xclip"


def test_set_clipboard_image_wl_copy():
    with (
        patch(
            "skill_manager.utils.linux.find_system_binary",
            side_effect=lambda name: "/usr/bin/wl-copy" if name == "wl-copy" else None,
        ),
        patch("skill_manager.utils.linux.os.path.isfile", return_value=True),
        patch("builtins.open", MagicMock()),
        patch("skill_manager.utils.linux.subprocess.run") as mock_run,
    ):
        mock_run.return_value = MagicMock(returncode=0)
        assert linux.set_clipboard_image("/tmp/test.png") is True


def test_send_ctrl_v_ydotool():
    with (
        patch("skill_manager.utils.linux.injection_allowed", return_value=True),
        patch("skill_manager.utils.linux.find_system_binary", return_value="/usr/bin/ydotool"),
        patch("skill_manager.utils.linux._ydotool_daemon_alive", return_value=True),
        patch("skill_manager.utils.linux.subprocess.run") as mock_run,
    ):
        mock_run.return_value = MagicMock(returncode=0)
        assert linux.send_ctrl_v() is True
        mock_run.assert_called_once_with(
            ["/usr/bin/ydotool", "key", "29:1", "47:1", "47:0", "29:0"],
            capture_output=True,
            text=True,
            timeout=5,
            env=ANY,
        )


def test_send_ctrl_v_daemon_down():
    """Daemon down: ydotool path must be skipped, no subprocess call."""
    with (
        patch("skill_manager.utils.linux.injection_allowed", return_value=True),
        patch("skill_manager.utils.linux.find_system_binary", return_value="/usr/bin/ydotool"),
        patch("skill_manager.utils.linux._ydotool_daemon_alive", return_value=False),
        patch("skill_manager.utils.linux.subprocess.run") as mock_run,
        patch("skill_manager.utils.linux.os.environ.get", return_value="wayland"),
    ):
        assert linux.send_ctrl_v() is False
        mock_run.assert_not_called()


def test_send_ctrl_v_all_fail():
    with (
        patch("skill_manager.utils.linux.injection_allowed", return_value=True),
        patch("skill_manager.utils.linux.find_system_binary", return_value=None),
        patch("skill_manager.utils.linux._has_ydotool", return_value=False),
        # pyautogui is installed on Windows CI: block its import so the
        # no-tool fallback path is exercised deterministically everywhere.
        patch.dict(sys.modules, {"pyautogui": None}),
    ):
        assert linux.send_ctrl_v() is False


def test_send_ctrl_v_blocked_under_pytest():
    """Injection guard: real keystrokes must never reach the live desktop
    when running under pytest (regression: ydotool was invoked for real).
    """
    with (
        patch("skill_manager.utils.linux.find_system_binary", return_value="/usr/bin/ydotool"),
        patch("skill_manager.utils.linux.subprocess.run") as mock_run,
    ):
        assert linux.send_ctrl_v() is False
        mock_run.assert_not_called()


def test_find_window_by_title_xdotool():
    with (
        patch(
            "skill_manager.utils.linux.find_system_binary",
            side_effect=lambda name: "/usr/bin/xdotool" if name == "xdotool" else None,
        ),
        patch("skill_manager.utils.linux.subprocess.run") as mock_run,
    ):
        mock_run.return_value = MagicMock(returncode=0, stdout="12345\n")
        result = linux.find_window_by_title("Skill Manager")
        assert result == 12345


def test_find_window_by_title_wayland_fallback():
    with (
        patch("skill_manager.utils.linux.find_system_binary", return_value=None),
        patch("skill_manager.utils.linux.os.environ.get", return_value="wayland"),
    ):
        result = linux.find_window_by_title("Skill Manager")
        assert result == 0


def test_find_window_by_title_not_found():
    with (
        patch("skill_manager.utils.linux.find_system_binary", return_value=None),
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
        patch("skill_manager.utils.linux.find_system_binary", return_value=None),
        # pyautogui is installed on Windows CI: block its import so the
        # no-tool fallback path is exercised deterministically everywhere.
        patch.dict(sys.modules, {"pyautogui": None}),
    ):
        assert linux.move_mouse(100, 200) is False


def test_type_text_no_tools():
    with (
        patch("skill_manager.utils.linux.injection_allowed", return_value=True),
        patch("skill_manager.utils.linux.find_system_binary", return_value=None),
        # pyautogui is installed on Windows CI: block its import so the
        # no-tool fallback path is exercised deterministically everywhere.
        patch.dict(sys.modules, {"pyautogui": None}),
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
            "skill_manager.controllers.snap_controller._portal_capture",
            return_value=None,
        ),
        patch(
            "skill_manager.controllers.snap_controller._gnome_snap_capture",
            return_value=None,
        ),
    ):
        assert linux.capture_screen() is None
        assert linux.capture_screen("/tmp/x.png") is None


def test_capture_screen_portal_succeeds():
    with patch(
        "skill_manager.controllers.snap_controller._portal_capture",
        return_value="/tmp/portal_test.png",
    ):
        result = linux.capture_screen()
        assert result == "/tmp/portal_test.png"
