from unittest.mock import MagicMock, patch

from skill_manager.utils import win32


def test_apply_native_style_windows_success_and_failure():
    window = MagicMock()
    with (
        patch("skill_manager.utils.win32.pywinstyles.apply_style") as apply_style,
    ):
        win32.apply_native_style(window, "mica")
    window.update.assert_called_once()
    apply_style.assert_called_once_with(window, "mica")

    with (
        patch("skill_manager.utils.win32.pywinstyles.apply_style", side_effect=OSError("nope")),
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
