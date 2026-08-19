"""Tests for the native title-bar immersive-dark helper.

Covers:
- ``_apply_immersive_dark`` writes the correct DWM attribute value (on/off).
- DWM failure is swallowed (no exception escapes).

The helper moved to ``skill_manager.utils.native_styling`` during the
Phase 1 decomposition; ``app`` re-exports it, but the patch target must be
the owning module so ``ctypes.windll`` is intercepted where the code looks
it up.
"""

from __future__ import annotations

import ctypes
from unittest.mock import patch

from skill_manager.utils.native_styling import DWMWA_USE_IMMERSIVE_DARK_MODE, _apply_immersive_dark

# ---------------------------------------------------------------------------
# Unit tests for _apply_immersive_dark
# ---------------------------------------------------------------------------


class TestApplyImmersiveDark:
    def test_sets_attribute_on(self) -> None:
        with patch("skill_manager.utils.native_styling.ctypes.windll", create=True) as mock_dwm:
            _apply_immersive_dark(0x12345, True)

        mock_dwm.dwmapi.DwmSetWindowAttribute.assert_called_once()
        args = mock_dwm.dwmapi.DwmSetWindowAttribute.call_args[0]
        assert args[0] == 0x12345  # hwnd
        assert args[1] == DWMWA_USE_IMMERSIVE_DARK_MODE
        # The value is passed via ctypes.byref(ctypes.c_int(1))
        val = ctypes.cast(args[2], ctypes.POINTER(ctypes.c_int)).contents.value
        assert val == 1
        assert args[3] == 4  # sizeof(DWORD)

    def test_sets_attribute_off(self) -> None:
        with patch("skill_manager.utils.native_styling.ctypes.windll", create=True) as mock_dwm:
            _apply_immersive_dark(0x12345, False)

        args = mock_dwm.dwmapi.DwmSetWindowAttribute.call_args[0]
        val = ctypes.cast(args[2], ctypes.POINTER(ctypes.c_int)).contents.value
        assert val == 0  # light

    def test_dwm_failure_does_not_raise(self) -> None:
        with patch("skill_manager.utils.native_styling.ctypes.windll", create=True):
            # Must not raise
            _apply_immersive_dark(0x12345, True)

    def test_constant_matches_windows_dwm_value(self) -> None:
        """DWMWA_USE_IMMERSIVE_DARK_MODE is the documented Win32 value 20."""
        assert DWMWA_USE_IMMERSIVE_DARK_MODE == 20

    def test_app_reexports_helper(self) -> None:
        """app.py must keep re-exporting the helper so old importers work."""
        import skill_manager.app as app_module

        assert app_module._apply_immersive_dark is _apply_immersive_dark
        assert app_module.DWMWA_USE_IMMERSIVE_DARK_MODE == DWMWA_USE_IMMERSIVE_DARK_MODE
