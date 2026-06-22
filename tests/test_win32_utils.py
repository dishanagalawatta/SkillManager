from unittest.mock import MagicMock, patch

from skill_manager.utils import win32


def test_apply_native_style_windows_success_and_failure():
    window = MagicMock()
    import ctypes

    if not hasattr(ctypes, "windll"):
        ctypes.windll = MagicMock()
    with (
        patch("skill_manager.utils.win32.pywinstyles") as apply_style,
    ):
        win32.apply_native_style(window, "mica")
    window.update.assert_called_once()
    apply_style.apply_style.assert_called_once_with(window, "mica")

    with (
        patch("skill_manager.utils.win32.pywinstyles"),
    ):
        win32.apply_native_style(MagicMock(), "mica")


def test_window_placement_windows_get_failure():
    with (
        patch("skill_manager.utils.win32.ctypes.windll", create=True) as windll,
    ):
        windll.user32.GetWindowPlacement.return_value = 0
        assert win32.get_window_placement(123) is None


def test_window_placement_windows_set_success():
    placement_data = (1, 2, (3, 4), (5, 6), (7, 8, 9, 10))
    with (
        patch("skill_manager.utils.win32.ctypes.windll", create=True) as windll,
    ):
        windll.user32.SetWindowPlacement.return_value = 1
        assert win32.set_window_placement(123, placement_data) is True


def test_send_paste_to_focused_window_success():
    with patch("skill_manager.utils.win32.ctypes.windll", create=True) as windll:
        windll.user32.keybd_event.return_value = None
        assert win32.send_paste_to_focused_window() is True
        assert windll.user32.keybd_event.call_count == 4
        calls = windll.user32.keybd_event.call_args_list
        assert calls[0].args == (0x11, 0, 0, 0)
        assert calls[1].args == (0x56, 0, 0, 0)
        assert calls[2].args == (0x56, 0, 0x0002, 0)
        assert calls[3].args == (0x11, 0, 0x0002, 0)


def test_send_paste_to_focused_window_failure():
    with patch("skill_manager.utils.win32.ctypes.windll", create=True) as windll:
        windll.user32.keybd_event.side_effect = OSError("access denied")
        assert win32.send_paste_to_focused_window() is False
