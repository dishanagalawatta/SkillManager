"""Tests for the MCP client launcher scripts (scripts/mcp_launcher.sh/.bat).

Why these exist: GUI-launched MCP clients (Claude Desktop, Cursor, IDEs, ...)
spawn the configured ``command`` with a minimal environment that never sources
shell rc files. ``uv`` from the standalone installer lives in
``~/.local/bin`` (POSIX) / ``%USERPROFILE%\\.local\\bin`` (Windows) — a
directory those processes cannot see — so ``"command": "uv"`` configs fail
with ``Executable not found in $PATH: "uv"``.

The launcher removes the PATH dependency: it prefers the project's own venv
Python (``python -m skill_manager.__main__``) and only falls back to ``uv``
(located on PATH, then ``~/.local/bin``). These tests exercise that pure
resolution logic by running the real script against fake project layouts
(``SKILL_MANAGER_PROJECT_ROOT`` override), asserting which interpreter the
launcher would hand the stdio connection to.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
LAUNCHER_SH = PROJECT_ROOT / "scripts" / "mcp_launcher.sh"
LAUNCHER_BAT = PROJECT_ROOT / "scripts" / "mcp_launcher.bat"

BASH = shutil.which("bash")

needs_bash = pytest.mark.skipif(
    BASH is None, reason="bash is required to exercise the POSIX launcher"
)

# Entry point every branch must reach, modulo interpreter prefix.
MAIN_MODULE = ("-m", "skill_manager.__main__")


def _write_logging_bin(bindir: Path, name: str, log: Path) -> Path:
    """Create an executable stub that logs its own path then its argv to ``log``.

    First line of the log is the stub's absolute path as exec'd; remaining
    lines are the arguments. This lets tests assert exactly which interpreter
    the launcher resolved, not just that something ran.
    """
    bindir.mkdir(parents=True, exist_ok=True)
    exe = bindir / name
    exe.write_text(
        "#!/bin/sh\n"
        'printf "%s\\n" "$0" > "$LAUNCHER_ARGV_LOG"\n'
        'printf "%s\\n" "$@" >> "$LAUNCHER_ARGV_LOG"\n',
        encoding="utf-8",
    )
    exe.chmod(0o755)
    return exe


def _run_launcher(
    project_root: Path, *args: str, env: dict[str, str]
) -> subprocess.CompletedProcess:
    assert BASH is not None
    full_env = {
        "PATH": env.get("PATH", os.environ["PATH"]),
        "HOME": env.get("HOME", os.environ.get("HOME", str(project_root))),
        "SKILL_MANAGER_PROJECT_ROOT": str(project_root),
        "LAUNCHER_ARGV_LOG": env["LAUNCHER_ARGV_LOG"],
    }
    return subprocess.run(
        [BASH, str(LAUNCHER_SH), *args],
        capture_output=True,
        text=True,
        env=full_env,
    )


def _read_argv(log: Path) -> list[str]:
    return log.read_text(encoding="utf-8").splitlines()


@needs_bash
def test_launcher_prefers_project_venv_python(tmp_path: Path) -> None:
    """With a project venv present, the launcher runs it directly (no uv)."""
    log = tmp_path / "argv.log"
    python_stub = _write_logging_bin(tmp_path / ".venv" / "bin", "python", log)

    result = _run_launcher(tmp_path, "--mcp", env={"LAUNCHER_ARGV_LOG": str(log)})

    assert result.returncode == 0, result.stderr
    assert _read_argv(log) == [str(python_stub), *MAIN_MODULE, "--mcp"]


@needs_bash
def test_launcher_passes_light_and_write_flags(tmp_path: Path) -> None:
    """Flags used by client configs (--mcp-light, --mcp-allow-write) pass through."""
    log = tmp_path / "argv.log"
    python_stub = _write_logging_bin(tmp_path / ".venv" / "bin", "python", log)

    for args in (("--mcp-light",), ("--mcp", "--mcp-allow-write")):
        result = _run_launcher(tmp_path, *args, env={"LAUNCHER_ARGV_LOG": str(log)})
        assert result.returncode == 0, result.stderr
        assert _read_argv(log) == [str(python_stub), *MAIN_MODULE, *args]


@needs_bash
def test_launcher_falls_back_to_uv_on_path(tmp_path: Path) -> None:
    """Without a venv, uv found on PATH is used with --directory <root>."""
    log = tmp_path / "argv.log"
    fake_bin = tmp_path / "bin"
    uv_stub = _write_logging_bin(fake_bin, "uv", log)

    result = _run_launcher(
        tmp_path,
        "--mcp",
        env={"LAUNCHER_ARGV_LOG": str(log), "PATH": str(fake_bin)},
    )

    assert result.returncode == 0, result.stderr
    assert _read_argv(log) == [
        str(uv_stub),
        "--directory",
        str(tmp_path),
        "run",
        "skill-manager",
        "--mcp",
    ]


@needs_bash
def test_launcher_falls_back_to_uv_in_home_local_bin(tmp_path: Path) -> None:
    """Without a venv or uv on PATH, the standalone installer location is tried."""
    log = tmp_path / "argv.log"
    fake_home = tmp_path / "home"
    uv_stub = _write_logging_bin(fake_home / ".local" / "bin", "uv", log)

    result = _run_launcher(
        tmp_path,
        "--mcp",
        env={
            "LAUNCHER_ARGV_LOG": str(log),
            "PATH": str(tmp_path / "empty"),
            "HOME": str(fake_home),
        },
    )

    assert result.returncode == 0, result.stderr
    assert _read_argv(log) == [
        str(uv_stub),
        "--directory",
        str(tmp_path),
        "run",
        "skill-manager",
        "--mcp",
    ]


@needs_bash
def test_launcher_fails_cleanly_without_python_or_uv(tmp_path: Path) -> None:
    """No venv and no uv anywhere -> non-zero exit with an actionable message."""
    log = tmp_path / "argv.log"
    fake_home = tmp_path / "home"

    result = _run_launcher(
        tmp_path,
        "--mcp",
        env={
            "LAUNCHER_ARGV_LOG": str(log),
            "PATH": str(tmp_path / "empty"),
            "HOME": str(fake_home),
        },
    )

    assert result.returncode == 1
    assert "uv sync" in result.stderr
    assert "MCP launcher" in result.stderr
    assert not log.exists()


def test_windows_launcher_targets_same_entry_point() -> None:
    """The .bat variant must exist and invoke the same module entry point."""
    assert LAUNCHER_BAT.exists(), "scripts/mcp_launcher.bat is missing"
    content = LAUNCHER_BAT.read_text(encoding="utf-8")
    assert "skill_manager.__main__" in content
    assert ".venv\\Scripts\\python.exe" in content
    assert "skill-manager" in content
