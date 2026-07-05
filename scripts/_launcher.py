"""Shared self-activating launcher helpers for scripts/*.py.

Provides ``ensure_venv()`` which detects whether the current interpreter
belongs to the project's ``.venv``.  If not, it re-executes the calling
script under the venv Python using a subprocess call.

Usage at the top of any scripts/ entry point::

    from _launcher import ensure_venv
    ensure_venv()
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

# ── Re-entry guard ────────────────────────────────────────────────────────────
# If set AND we're still on the wrong Python after re-exec, abort immediately.

_REENTRY_ENV_VAR = "SKILL_MANAGER_LAUNCHER_REENTRY"


def _project_root() -> Path:
    """Return the project root (one level above ``scripts/``)."""
    return Path(__file__).resolve().parent.parent


def _venv_python() -> Path:
    """Return the expected venv Python path for the current platform."""
    root = _project_root()
    if sys.platform == "win32":
        return root / ".venv" / "Scripts" / "python.exe"
    return root / ".venv" / "bin" / "python"


def _is_venv_python() -> bool:
    """True if ``sys.executable`` is the project's venv Python."""
    try:
        return Path(sys.executable).resolve() == _venv_python().resolve()
    except OSError:
        return False


def ensure_venv() -> None:
    """Ensure the calling script runs under the project's venv Python.

    If the current interpreter is not the venv Python, this re-executes
    the calling script (``sys.argv[0]``) as a subprocess and calls
    ``os._exit`` with the child's return code.

    Never returns on a successful re-exec.
    """
    if _is_venv_python():
        return  # already in the venv

    if os.environ.get(_REENTRY_ENV_VAR) == "1":
        print(
            "ERROR: Re-exec cycle detected.  The venv Python exists but could not "
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
            "ERROR: No .venv found.  Install dependencies with:\n\n  uv sync\n",
            file=sys.stderr,
        )
        sys.exit(1)

    os.environ[_REENTRY_ENV_VAR] = "1"
    print(
        f"[launcher] Re-executing under venv Python: {venv_py}",
        file=sys.stderr,
    )
    try:
        ret = subprocess.call([str(venv_py), *sys.argv])
        os._exit(ret)
    except Exception as exc:
        print(f"ERROR: Failed to launch virtualenv Python: {exc}", file=sys.stderr)
        os._exit(1)
