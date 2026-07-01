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
"""

import os
import sys
from pathlib import Path

# ── Environment marker: set by the launcher after the first re-exec. ──────────
# If this is set AND we're still on the wrong Python, something is
# wrong with the venv (e.g. it exists but is incomplete).  We abort
# rather than looping.
_REENTRY_ENV_VAR = "SKILL_MANAGER_LAUNCHER_REENTRY"

# ── Venv detection ────────────────────────────────────────────────────────────


def _project_root() -> Path:
    """Return the project root directory (one level above ``scripts/``)."""
    return Path(__file__).resolve().parent.parent


def _venv_python() -> Path:
    """Return the expected venv Python path for the current platform."""
    root = _project_root()
    if sys.platform == "win32":
        return root / ".venv" / "Scripts" / "python.exe"
    return root / ".venv" / "bin" / "python"


def _is_venv_python() -> bool:
    """Check whether ``sys.executable`` points to the project's venv Python."""
    try:
        expected = _venv_python()
        # Resolve both to handle symlinks, case-insensitive Windows paths, etc.
        return Path(sys.executable).resolve() == expected.resolve()
    except OSError:
        return False


# ── Re-exec logic (must run BEFORE any project imports) ───────────────────────


def _ensure_venv() -> None:
    """If we are not running the venv Python, re-exec with it.

    Called at module level before any project imports.  This is the
    same pattern used by Poetry, Pipenv, PDM, and Hatch — a proper
    self-activating launcher, not a workaround.

    Side effects:
        - Calls ``os.execv`` to replace the current process if the
          venv Python is found and is different from ``sys.executable``.
        - Calls ``sys.exit(1)`` if no venv is found.
        - Calls ``sys.exit(2)`` on re-entry cycle (re-exec failed to
          switch to the venv Python).
    """
    if _is_venv_python():
        return  # Already on the right Python — nothing to do.

    # If we re-exec'd once and still ended up on the wrong Python,
    # the venv is broken or the re-exec logic hit an edge case.
    if os.environ.get(_REENTRY_ENV_VAR) == "1":
        print(
            "ERROR: Re-exec cycle detected. The venv Python exists but could not "
            "be used.\n"
            f"  Expected: {_venv_python()}\n"
            f"  Current:  {sys.executable}\n\n"
            "Try: rm -rf .venv && uv sync",
            file=sys.stderr,
        )
        sys.exit(2)

    venv_py = _venv_python()
    if not venv_py.exists():
        print(
            "ERROR: No .venv found. Install dependencies with:\n\n  uv sync\n",
            file=sys.stderr,
        )
        sys.exit(1)

    # Re-exec with the venv Python.
    os.environ[_REENTRY_ENV_VAR] = "1"
    import subprocess

    try:
        ret = subprocess.call([str(venv_py), __file__, *sys.argv[1:]])
        os._exit(ret)
    except Exception as e:
        print(f"ERROR: Failed to launch virtualenv Python: {e}", file=sys.stderr)
        os._exit(1)


_ensure_venv()

# ── Safe to import project modules below this line ────────────────────────────

src_path = _project_root() / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from skill_manager.__main__ import main  # noqa: E402

if __name__ == "__main__":
    main()
