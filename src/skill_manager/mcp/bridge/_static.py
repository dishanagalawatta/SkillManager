"""Repo-rooted static analysis (gitignore-aware grep) for the MCP bridge."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

from ._telemetry import _log_call

# Project root (repo root) — used for subprocess-based tools (lint/test/build)
# and for static analysis. Resolved relative to this file:
#   src/skill_manager/mcp/bridge/_static.py -> repo root is 4 levels up.
_REPO_ROOT = Path(__file__).resolve().parents[4]


def static_analyze(pattern: str, path: str = "src") -> list[dict[str, Any]]:
    """Safe grep over the repo, respecting ``.gitignore`` via pathspec.

    Returns a list of ``{"file", "line", "text"}`` dicts. Uses ``pathspec`` when
    available (matching the project's gitignore semantics); otherwise falls back
    to skipping ``.git`` and common junk directories.
    """
    _log_call("static_analyze")
    root = _REPO_ROOT / path
    if not root.exists():
        return []

    try:
        compiled = re.compile(pattern)
    except re.error as exc:
        return [{"error": f"invalid_pattern: {exc}"}]

    spec = _load_gitignore(root)

    matches: list[dict[str, Any]] = []
    try:
        for file_path in _walk(root):
            rel = file_path.relative_to(_REPO_ROOT)
            if spec is not None and spec.match_file(str(rel)):
                continue
            try:
                with file_path.open("r", encoding="utf-8", errors="ignore") as fh:
                    for lineno, line in enumerate(fh, start=1):
                        if compiled.search(line):
                            matches.append(
                                {
                                    "file": str(rel).replace(os.sep, "/"),
                                    "line": lineno,
                                    "text": line.rstrip("\n"),
                                }
                            )
            except (OSError, UnicodeDecodeError):
                continue
    except Exception as exc:  # noqa: BLE001
        return [{"error": str(exc)}]

    return matches


def _load_gitignore(root: Path) -> Any | None:  # noqa: ARG001
    """Build a pathspec matcher from the repo .gitignore, if present."""
    gitignore = _REPO_ROOT / ".gitignore"
    if not gitignore.exists():
        return None
    try:
        import pathspec  # type: ignore[import-not-found]

        patterns = [
            line.strip()
            for line in gitignore.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.startswith("#")
        ]
        return pathspec.PathSpec.from_lines("gitwildmatch", patterns)
    except Exception:  # noqa: BLE001 - pathspec may be absent; degrade gracefully
        return None


def _walk(root: Path) -> Any:
    """Yield files under root, skipping .git and obvious junk dirs."""
    skip_dirs = {".git", "__pycache__", ".venv", "venv", "node_modules", "build", "dist"}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in skip_dirs]
        for fname in filenames:
            yield Path(dirpath) / fname
