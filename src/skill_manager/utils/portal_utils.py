"""Portal-related Python interpreter discovery utilities.

Shared by both the snap capture subsystem (``portal_capture.py``) and the
global hotkey subsystem (``portal_hotkeys.py``).  Lives in ``utils/`` so
that ``core/`` modules can import it without depending on ``controllers/``.
"""

from __future__ import annotations

import os
import subprocess
import sys


def find_portal_python() -> str | None:
    """Find a Python interpreter with ``dbus`` and ``gi.repository`` available.

    Priority order (deduplicated):
    1. ``/usr/bin/python3`` — system Python (has ``python3-dbus`` /
       ``python3-gi`` on standard GNOME installs).
    2. ``sys.executable`` — current venv Python.
    3. Any ``python3`` on ``PATH``.
    """
    seen: set[str] = set()
    for candidate in ("/usr/bin/python3", sys.executable, "python3"):
        if candidate in seen:
            continue
        seen.add(candidate)
        if not os.path.isfile(candidate):
            continue
        try:
            result = subprocess.run(
                [candidate, "-c", "import dbus, gi.repository; print('ok')"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                return candidate
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
    return None
