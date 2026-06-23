"""Tests for the native title-bar immersive-dark helper.

Covers:
- ``_apply_immersive_dark`` writes the correct DWM attribute value (on/off).
- DWM failure is swallowed (no exception escapes).
"""

from __future__ import annotations

import ctypes
from unittest.mock import patch

from skill_manager.app import DWMWA_USE_IMMERSIVE_DARK_MODE, _apply_immersive_dark

# ---------------------------------------------------------------------------
# Unit tests for _apply_immersive_dark
# ---------------------------------------------------------------------------


class TestApplyImmersiveDark:
    def test_sets_attribute_on(self) -> None:
        with patch("ctypes.windll.dwmapi.DwmSetWindowAttribute") as mock_dwm:
            _apply_immersive_dark(0x12345, True)

        mock_dwm.assert_called_once()
        args = mock_dwm.call_args[0]
        assert args[0] == 0x12345  # hwnd
        assert args[1] == DWMWA_USE_IMMERSIVE_DARK_MODE
        # The value is passed via ctypes.byref(ctypes.c_int(1))
        val = ctypes.cast(args[2], ctypes.POINTER(ctypes.c_int)).contents.value
        assert val == 1
        assert args[3] == 4  # sizeof(DWORD)

    def test_sets_attribute_off(self) -> None:
        with patch("ctypes.windll.dwmapi.DwmSetWindowAttribute") as mock_dwm:
            _apply_immersive_dark(0x12345, False)

        args = mock_dwm.call_args[0]
        val = ctypes.cast(args[2], ctypes.POINTER(ctypes.c_int)).contents.value
        assert val == 0  # light

    def test_dwm_failure_does_not_raise(self) -> None:
        with patch("ctypes.windll.dwmapi.DwmSetWindowAttribute", side_effect=OSError("no DWM")):
            # Must not raise
            _apply_immersive_dark(0x12345, True)
