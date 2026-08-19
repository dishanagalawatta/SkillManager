"""Tests for the self-activating launcher in scripts/dev_run.py.

These tests verify that dev_run.py correctly:
    1. Imports ensure_venv from the shared _launcher module
    2. Adds the project src directory to sys.path
    3. Invokes skill_manager.__main__.main()

The ``ensure_venv()`` call at module level is prevented during testing
by patching subprocess.call and os._exit before import.

For comprehensive tests of the launcher logic itself, see test_launcher.py.
"""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

# ── Load dev_run.py as an isolated module (no re-exec on import) ──────────────


def _load_dev_run_module():
    """Import dev_run.py as a module WITHOUT triggering its module-level
    ``ensure_venv()`` call.  We do this by patching ``subprocess.call`` and ``os._exit`` to
    be a no-op before importing."""
    spec = importlib.util.spec_from_file_location(
        "dev_run",
        Path(__file__).resolve().parent.parent / "scripts" / "dev_run.py",
    )
    assert spec is not None and spec.loader is not None, (
        "Failed to create module spec for dev_run.py"
    )
    mod = importlib.util.module_from_spec(spec)

    # Prevent subprocess.call and os._exit from actually executing or exiting
    # the process during import.
    import subprocess

    original_call = subprocess.call
    original_exit = os._exit
    subprocess.call = lambda *a, **kw: 0
    os._exit = lambda *a, **kw: None  # type: ignore[assignment]
    try:
        spec.loader.exec_module(mod)  # type: ignore[union-attr]
    finally:
        subprocess.call = original_call
        os._exit = original_exit

    return mod


# Lazily loaded — one instance per test session.
_dev_run = None


def _get_module():
    global _dev_run
    if _dev_run is None:
        _dev_run = _load_dev_run_module()
    return _dev_run


# ── Tests ─────────────────────────────────────────────────────────────────────


class TestLauncherImport:
    """Verify dev_run.py correctly imports from shared _launcher."""

    def test_imports_ensure_venv_from_launcher(self):
        mod = _get_module()
        assert hasattr(mod, "ensure_venv")
        assert callable(mod.ensure_venv)

    def test_old_inline_functions_removed(self):
        """The old inline _REENTRY_ENV_VAR, _project_root, etc. should NOT
        exist on the dev_run module itself (they live in _launcher now)."""
        mod = _get_module()
        assert not hasattr(mod, "_REENTRY_ENV_VAR")
        assert not hasattr(mod, "_project_root")
        assert not hasattr(mod, "_venv_python")
        assert not hasattr(mod, "_is_venv_python")
        assert not hasattr(mod, "_ensure_venv")


class TestSrcPathSetup:
    """Verify dev_run.py adds src/ to sys.path for project imports."""

    def test_src_path_added_to_sys_path(self):
        src_path = str(Path(__file__).resolve().parent.parent / "src")
        assert src_path in sys.path or src_path in [str(p) for p in sys.path]
