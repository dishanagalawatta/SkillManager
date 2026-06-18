"""Tests for the global hotkey manager."""

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
    def test_signal_emitted(self):
        manager = GlobalHotkeyManager()
        received = []
        manager.hotkeyPressed.connect(lambda hid: received.append(hid))
        manager.hotkeyPressed.emit(42)
        assert received == [42]
