#!/usr/bin/env bash
#
# mcp_launcher.sh — Launch the SkillManager MCP server for MCP clients.
#
# Why this exists: GUI-launched MCP clients (Claude Desktop, Cursor, IDEs, ...)
# spawn the configured `command` with a minimal environment that never sources
# shell rc files. `uv` is installed by the standalone installer to
# ~/.local/bin (POSIX) or %USERPROFILE%\.local\bin (Windows) — directories
# those processes cannot see — so `"command": "uv"` configs fail with
# `Executable not found in $PATH: "uv"`.
#
# This launcher removes the PATH dependency:
#   1. Preferred: run the project's own venv Python directly
#      (`.venv/bin/python -m skill_manager.__main__`) — no uv required.
#   2. Fallback: locate `uv` on PATH, then in ~/.local/bin, and let uv
#      sync/run the environment on demand.
#
# Client config:
#   "command": "/absolute/path/to/skill-manager/scripts/mcp_launcher.sh",
#   "args": ["--mcp"]          # or --mcp-light / --mcp-allow-write
#
# Test/dev override: SKILL_MANAGER_PROJECT_ROOT=<root> forces the project root
# (used by tests and unusual layouts).
set -euo pipefail

# Resolve the project root from this script's location (scripts/ -> repo root),
# unless overridden via SKILL_MANAGER_PROJECT_ROOT.
if [[ -n "${SKILL_MANAGER_PROJECT_ROOT:-}" ]]; then
    PROJECT_ROOT="${SKILL_MANAGER_PROJECT_ROOT}"
else
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
fi

# Run from the project root so relative paths behave exactly like
# `uv --directory <root> run skill-manager`.
cd "${PROJECT_ROOT}"

# 1) Preferred: the project venv Python — no uv needed at runtime.
VENV_PYTHON="${PROJECT_ROOT}/.venv/bin/python"
if [[ -x "${VENV_PYTHON}" ]]; then
    exec "${VENV_PYTHON}" -m skill_manager.__main__ "$@"
fi

# 2) Fallback: uv (syncs/creates the venv on demand).
UV_BIN=""
if command -v uv >/dev/null 2>&1; then
    UV_BIN="$(command -v uv)"
elif [[ -x "${HOME}/.local/bin/uv" ]]; then
    UV_BIN="${HOME}/.local/bin/uv"
fi

if [[ -n "${UV_BIN}" ]]; then
    exec "${UV_BIN}" --directory "${PROJECT_ROOT}" run skill-manager "$@"
fi

# 3) Nothing usable — explain how to fix it.
echo "SkillManager MCP launcher: no ${VENV_PYTHON} and no uv found." >&2
echo "Run 'uv sync' in ${PROJECT_ROOT} first, or install uv." >&2
exit 1
