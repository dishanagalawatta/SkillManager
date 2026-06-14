"""Tests for the global hotkey manager."""

from unittest.mock import patch

from skill_manager.core.global_hotkey import (
    GlobalHotkeyManager,
    _qt_sequence_to_pynput,
)


class TestQtSequenceToPynput:
    def test_ctrl_shift_s(self):
        result = _qt_sequence_to_pynput("Ctrl+Shift+S")
        assert result == "<ctrl>+<shift>+s"

    def test_ctrl_f(self):
        result = _qt_sequence_to_pynput("Ctrl+F")
        assert result == "<ctrl>+f"

    def test_meta_replacement(self):
        result = _qt_sequence_to_pynput("Meta+Shift+S")
        assert result == "<cmd>+<shift>+s"

    def test_return_replacement(self):
        result = _qt_sequence_to_pynput("Ctrl+Return")
        assert result == "<ctrl>+<enter>"

    def test_escape_replacement(self):
        result = _qt_sequence_to_pynput("Shift+Escape")
        assert result == "<shift>+<esc>"


class TestGlobalHotkeyManager:
    @patch("skill_manager.core.global_hotkey.sys")
    def test_register_noop_on_non_windows(self, mock_sys):
        mock_sys.platform = "linux"
        manager = GlobalHotkeyManager()
        manager.register(1, "Ctrl+Shift+S")
        # Should not crash, just log debug message

    @patch("skill_manager.core.global_hotkey.sys")
    def test_unregister_noop_on_non_windows(self, mock_sys):
        mock_sys.platform = "linux"
        manager = GlobalHotkeyManager()
        manager.unregister(1)

    @patch("skill_manager.core.global_hotkey.sys")
    def test_stop_noop_on_non_windows(self, mock_sys):
        mock_sys.platform = "linux"
        manager = GlobalHotkeyManager()
        manager.stop()

    def test_signal_emitted(self):
        manager = GlobalHotkeyManager()
        received = []
        manager.hotkeyPressed.connect(lambda hid: received.append(hid))
        manager.hotkeyPressed.emit(42)
        assert received == [42]
