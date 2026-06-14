"""Tests for the global hotkey manager."""

from unittest.mock import patch

from skill_manager.core.global_hotkey import (
    GlobalHotkeyManager,
    _qt_key_to_win32_vkey,
    _qt_modifiers_to_win32,
    parse_key_sequence,
)


class TestQtKeyToWin32Vkey:
    def test_letters(self):
        from PySide6.QtCore import Qt

        assert _qt_key_to_win32_vkey(Qt.Key.Key_A) == 0x41
        assert _qt_key_to_win32_vkey(Qt.Key.Key_Z) == 0x5A

    def test_numbers(self):
        from PySide6.QtCore import Qt

        assert _qt_key_to_win32_vkey(Qt.Key.Key_0) == 0x30
        assert _qt_key_to_win32_vkey(Qt.Key.Key_9) == 0x39

    def test_f_keys(self):
        from PySide6.QtCore import Qt

        assert _qt_key_to_win32_vkey(Qt.Key.Key_F1) == 0x70
        assert _qt_key_to_win32_vkey(Qt.Key.Key_F12) == 0x7B

    def test_special_keys(self):
        from PySide6.QtCore import Qt

        assert _qt_key_to_win32_vkey(Qt.Key.Key_Escape) == 0x1B
        assert _qt_key_to_win32_vkey(Qt.Key.Key_Return) == 0x0D
        assert _qt_key_to_win32_vkey(Qt.Key.Key_Delete) == 0x2E


class TestQtModifiersToWin32:
    def test_control(self):
        from PySide6.QtCore import Qt

        result = _qt_modifiers_to_win32(Qt.KeyboardModifier.ControlModifier)
        assert result & 0x0002  # MOD_CONTROL

    def test_alt(self):
        from PySide6.QtCore import Qt

        result = _qt_modifiers_to_win32(Qt.KeyboardModifier.AltModifier)
        assert result & 0x0001  # MOD_ALT

    def test_shift(self):
        from PySide6.QtCore import Qt

        result = _qt_modifiers_to_win32(Qt.KeyboardModifier.ShiftModifier)
        assert result & 0x0004  # MOD_SHIFT

    def test_combo(self):
        from PySide6.QtCore import Qt

        result = _qt_modifiers_to_win32(
            Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier
        )
        assert result & 0x0002  # MOD_CONTROL
        assert result & 0x0004  # MOD_SHIFT


class TestParseKeySequence:
    def test_ctrl_shift_s(self):
        result = parse_key_sequence("Ctrl+Shift+S")
        assert result is not None
        mods, vkey = result
        assert mods & 0x0002  # MOD_CONTROL
        assert mods & 0x0004  # MOD_SHIFT
        assert vkey == 0x53  # 'S'

    def test_ctrl_f(self):
        result = parse_key_sequence("Ctrl+F")
        assert result is not None
        mods, vkey = result
        assert mods & 0x0002  # MOD_CONTROL
        assert vkey == 0x46  # 'F'

    def test_empty_string(self):
        result = parse_key_sequence("")
        assert result is None

    def test_invalid_string(self):
        result = parse_key_sequence("NotAKey")
        assert result is None


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
    def test_start_noop_on_non_windows(self, mock_sys):
        mock_sys.platform = "linux"
        manager = GlobalHotkeyManager()
        manager.start()
        assert not manager._is_running

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
