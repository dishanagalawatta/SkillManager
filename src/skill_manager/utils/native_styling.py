"""Native window styling helpers (Windows DWM immersive dark + pywinstyles Mica).

Extracted from ``app.py`` during Phase 1 of the codebase refactor; re-exported
from ``skill_manager.app`` so the public surface is unchanged.
"""

import contextlib
import ctypes

# Try to import pywinstyles for Mica/Acrylic
try:
    import pywinstyles  # noqa: F401  — re-exported for callers that apply Mica

    HAS_PYWINSTYLES = True
except ImportError:
    pywinstyles = None  # type: ignore[assignment]
    HAS_PYWINSTYLES = False

# DWM attribute for immersive dark mode title bar
DWMWA_USE_IMMERSIVE_DARK_MODE = 20


def _apply_immersive_dark(hwnd: int, enabled: bool) -> None:
    """Set the DWM immersive-dark-mode attribute on the window.

    ``enabled=True`` tells the OS to render the title bar and system
    buttons in dark style; ``enabled=False`` reverts to light.
    """
    with contextlib.suppress(Exception):
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd,
            DWMWA_USE_IMMERSIVE_DARK_MODE,
            ctypes.byref(ctypes.c_int(1 if enabled else 0)),
            4,
        )
