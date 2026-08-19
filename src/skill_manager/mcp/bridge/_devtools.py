"""Subprocess-based dev tools (lint / test / build) for the MCP bridge."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any

from ._static import _REPO_ROOT
from ._telemetry import _log_call


# ---------------------------------------------------------------------------
# Subprocess-based dev tools (lint / test / build)
# ---------------------------------------------------------------------------
def _run_subprocess(cmd: list[str], cwd: Path | None = None) -> dict[str, Any]:
    """Run a command, returning a structured result. Never raises.

    Uses ``CREATE_NO_WINDOW`` on Windows to prevent console windows
    from flashing when subprocesses (uv, ruff, pytest) are launched
    from the MCP server in GUI mode.
    """
    try:
        kwargs: dict[str, Any] = {
            "cwd": str(cwd) if cwd else None,
            "capture_output": True,
            "text": True,
            "timeout": 600,
        }
        if sys.platform == "win32":
            kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
        proc = subprocess.run(cmd, **kwargs)
        return {
            "returncode": proc.returncode,
            "stdout": proc.stdout or "",
            "stderr": proc.stderr or "",
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "returncode": -1,
            "stdout": exc.stdout if isinstance(exc.stdout, str) else "",
            "stderr": f"timeout after {exc.timeout}s",
        }
    except Exception as exc:  # noqa: BLE001
        return {"returncode": -1, "stdout": "", "stderr": str(exc)}


def run_lint(path: str = "src", fix: bool = False) -> dict[str, Any]:
    """Run ``uv run ruff`` over the given path."""
    _log_call("run_lint")
    cmd = ["uv", "run", "ruff", "check"]
    if fix:
        cmd.append("--fix")
    cmd.append(path)
    result = _run_subprocess(cmd, cwd=_REPO_ROOT)
    result["passed"] = result["returncode"] == 0
    return result


def run_tests(target: str = "", parallel: bool = True) -> dict[str, Any]:
    """Run pytest, optionally scoped to a single file/node id."""
    _log_call("run_tests")
    cmd = ["uv", "run", "pytest"]
    if parallel:
        cmd += ["-n", "auto"]
    if target:
        cmd.append(target)
    result = _run_subprocess(cmd, cwd=_REPO_ROOT)
    result["passed"] = result["returncode"] == 0
    return result


def run_build(target: str = "") -> dict[str, Any]:
    """Run the application build."""
    _log_call("run_build")
    cmd = ["uv", "run", "skill-manager-build"]
    if target:
        cmd.append(target)
    result = _run_subprocess(cmd, cwd=_REPO_ROOT)
    result["success"] = result["returncode"] == 0
    return result
