"""Tests for the self-activating launcher in scripts/dev_run.py.

These tests verify that the launcher correctly:
    1. Detects when it's running outside the venv
    2. Re-execs with the venv Python when the venv exists
    3. Prints a clear error when no venv exists
    4. Stops re-exec cycles (re-entry guard)
    5. No-ops when already on the venv Python

The launcher functions are imported in isolation — the module-level
``_ensure_venv()`` call in ``dev_run.py`` is NOT triggered during
tests.  We test the functions directly via ``importlib.util``.
"""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path

import pytest

# ── Load dev_run.py as an isolated module (no re-exec on import) ──────────────


def _load_dev_run_module():
    """Import dev_run.py as a module WITHOUT triggering its module-level
    ``_ensure_venv()`` call.  We do this by patching ``subprocess.call`` and ``os._exit`` to
    be a no-op before importing."""
    spec = importlib.util.spec_from_file_location(
        "dev_run",
        Path(__file__).resolve().parent.parent / "scripts" / "dev_run.py",
    )
    assert spec is not None and spec.loader is not None, (
        "Failed to create module spec for dev_run.py"
    )
    mod = importlib.util.module_from_spec(spec)

    # Prevent subprocess.call and os._exit from actually executing or exiting the process during import.
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


class TestVenvPythonDetection:
    """Verify ``_is_venv_python`` returns correct results."""

    def test_returns_true_when_on_venv_python(self, monkeypatch):
        mod = _get_module()
        venv_py = mod._venv_python()
        monkeypatch.setattr("sys.executable", str(venv_py))
        assert mod._is_venv_python() is True

    def test_returns_false_when_on_different_python(self, monkeypatch):
        mod = _get_module()
        monkeypatch.setattr("sys.executable", "/usr/bin/python3.12")
        assert mod._is_venv_python() is False

    def test_returns_false_when_executable_is_empty(self, monkeypatch):
        mod = _get_module()
        monkeypatch.setattr("sys.executable", "")
        # Empty string → Path resolves to cwd, not the venv → False
        assert mod._is_venv_python() is False

    def test_handles_oserror_gracefully(self, monkeypatch):
        mod = _get_module()

        # Make _venv_python raise an OSError so the except branch in
        # _is_venv_python fires.  This tests the guard without touching
        # Path.resolve globally (which would break _project_root).
        def _boom():
            raise OSError("nope")

        monkeypatch.setattr(mod, "_venv_python", _boom)
        # _is_venv_python calls _venv_python() first — the OSError
        # should be caught and return False.
        assert mod._is_venv_python() is False


class TestEnsureVenv:
    """Verify ``_ensure_venv`` behavior in each branch."""

    def test_noop_when_already_on_venv_python(self, monkeypatch):
        mod = _get_module()
        venv_py = mod._venv_python()
        monkeypatch.setattr("sys.executable", str(venv_py))
        # Should not call sys.exit or os.execv
        mod._ensure_venv()  # no exception → pass

    def test_reexec_when_wrong_python(self, monkeypatch, tmp_path):
        mod = _get_module()
        # Create a fake venv Python
        fake_venv = tmp_path / ".venv" / "Scripts" / "python.exe"
        fake_venv.parent.mkdir(parents=True)
        fake_venv.write_text("fake python")

        monkeypatch.setattr("sys.executable", "/usr/bin/python3.12")
        monkeypatch.setattr(mod, "_venv_python", lambda: fake_venv)
        monkeypatch.setattr(mod, "_project_root", lambda: tmp_path)

        subprocess_calls = []
        _exit_calls = []
        import subprocess

        monkeypatch.setattr(subprocess, "call", lambda args: subprocess_calls.append(args) or 0)
        monkeypatch.setattr(os, "_exit", lambda code: _exit_calls.append(code))

        mod._ensure_venv()

        assert len(subprocess_calls) == 1
        assert subprocess_calls[0][0] == str(fake_venv)
        assert len(_exit_calls) == 1
        assert _exit_calls[0] == 0

    def test_reentry_cycle_calls_sys_exit(self, monkeypatch):
        mod = _get_module()
        monkeypatch.setattr("sys.executable", "/usr/bin/python3.12")
        # Simulate re-entry: the env var is already set.
        monkeypatch.setenv(mod._REENTRY_ENV_VAR, "1")

        with pytest.raises(SystemExit) as exc_info:
            mod._ensure_venv()

        assert exc_info.value.code == 2

    def test_missing_venv_calls_sys_exit(self, monkeypatch, tmp_path):
        mod = _get_module()
        monkeypatch.setattr("sys.executable", "/usr/bin/python3.12")
        monkeypatch.delenv(mod._REENTRY_ENV_VAR, raising=False)
        # Point _venv_python at a non-existent path in tmp_path
        missing_venv = tmp_path / ".venv" / "bin" / "python"
        monkeypatch.setattr(mod, "_venv_python", lambda: missing_venv)

        with pytest.raises(SystemExit) as exc_info:
            mod._ensure_venv()

        assert exc_info.value.code == 1


class TestReentryGuard:
    """Verify the re-entry environment variable logic."""

    def test_reentry_env_var_is_set_before_reexec(self, monkeypatch, tmp_path):
        mod = _get_module()
        fake_venv = tmp_path / ".venv" / "bin" / "python"
        fake_venv.parent.mkdir(parents=True)
        fake_venv.write_text("fake python")

        monkeypatch.setattr("sys.executable", "/usr/bin/python3.12")
        monkeypatch.delenv(mod._REENTRY_ENV_VAR, raising=False)
        monkeypatch.setattr(mod, "_venv_python", lambda: fake_venv)
        monkeypatch.setattr(mod, "_project_root", lambda: tmp_path)

        env_captured = {}

        def capture_call(args):
            env_captured.update(os.environ)
            return 0

        import subprocess

        monkeypatch.setattr(subprocess, "call", capture_call)
        monkeypatch.setattr(os, "_exit", lambda code: None)

        mod._ensure_venv()

        assert env_captured.get(mod._REENTRY_ENV_VAR) == "1"


class TestProjectRoot:
    """Verify ``_project_root`` resolves correctly."""

    def test_resolves_to_parent_of_scripts(self):
        mod = _get_module()
        root = mod._project_root()
        assert root.name in ("SkillManager", "app", "workspace")
        assert (root / "scripts" / "dev_run.py").exists()
