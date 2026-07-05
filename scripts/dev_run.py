"""Self-activating launcher for SkillManager development.

Usage:
    python scripts/dev_run.py              # works with any Python on PATH
    uv run python scripts/dev_run.py       # canonical (uv-managed)
    uv run skill-manager                   # preferred (installed script)

How it works:
    If the script detects that the current Python interpreter does NOT
    belong to the project's ``.venv``, it will automatically re-exec
    itself with the correct venv Python.  This means you can run::

        python scripts/dev_run.py

    from any shell, with any ``python`` on your PATH, and the script
    will find and use the project's virtual environment.

    If no ``.venv`` exists, the script prints a clear error and exits
    with a non-zero status.

Shared implementation lives in ``_launcher.py`` (same directory).
"""

import os
import sys
from pathlib import Path

# ── Venv guard (shared via _launcher.py) ──────────────────────────────────────
_scripts_dir = os.path.dirname(os.path.abspath(__file__))
if _scripts_dir not in sys.path:
    sys.path.insert(0, _scripts_dir)
from _launcher import ensure_venv  # noqa: E402

ensure_venv()

# ── Safe to import project modules below this line ────────────────────────────

src_path = Path(__file__).resolve().parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from skill_manager.__main__ import main  # noqa: E402

if __name__ == "__main__":
    main()
