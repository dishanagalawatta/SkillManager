"""Containment rules for the write-capable MCP tools.

The MCP write tools may only touch files inside a directory SkillManager
actually manages:

* a configured **skill source** (where new skills are collected), or
* a configured **project** (where commands and skills are deployed).

Anything else is refused *before* a byte is written: an arbitrary path, a
path traversal (``../../etc``), or a symlink that escapes a root.  The
rules live here so every write tool enforces the same policy.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

#: Directory names that may never be written to, regardless of the root.
#: Mirrors the AGENTS.md exclusions enforced by the write tools.
EXCLUDED_MARKERS: tuple[str, ...] = (
    ".agents/skills",
    ".agents/commands",
    "TODO.md",
)


def _resolve(path: Path) -> Path:
    """Resolve *path* as far as the filesystem allows.

    ``strict=False`` keeps a not-yet-existing target resolvable (a skill
    folder that is about to be created), while still resolving every
    symlink on the way — that is what stops a symlink from escaping a
    root.
    """
    try:
        return path.resolve()
    except (OSError, RuntimeError):
        try:
            return Path(os.path.abspath(str(path)))
        except Exception:  # noqa: BLE001
            return path


def is_within(candidate: str | Path, roots: list[Path]) -> bool:
    """True when *candidate* resolves inside one of *roots*."""
    if not roots:
        return False
    try:
        resolved = _resolve(Path(candidate))
    except Exception:  # noqa: BLE001
        return False

    for root in roots:
        try:
            root_resolved = _resolve(Path(root))
        except Exception:  # noqa: BLE001
            continue
        if resolved == root_resolved:
            return True
        try:
            if root_resolved in resolved.parents:
                return True
        except Exception:  # noqa: BLE001
            continue
    return False


def skill_source_roots(controller: Any) -> list[Path]:
    """The configured skill sources — the only place a skill may be created."""
    roots: list[Path] = []
    for raw in list(getattr(controller, "_sources", None) or []):
        try:
            roots.append(Path(str(raw)))
        except Exception:  # noqa: BLE001
            continue
    return roots


def project_roots(controller: Any) -> list[Path]:
    """The configured projects — the only place a command may be deployed."""
    roots: list[Path] = []
    for raw in list(getattr(controller, "_projects", None) or []):
        try:
            roots.append(Path(str(raw)))
        except Exception:  # noqa: BLE001
            continue
    return roots


def safe_skill_name(name: str) -> str | None:
    """Validate a skill folder name.

    A name is a *single* path segment: no separators, no ``..``, no
    absolute path, no drive letter.  ``None`` means the name is unsafe.
    """
    if not name:
        return None
    clean = str(name).strip()
    if not clean:
        return None
    if "/" in clean or "\\" in clean:
        return None
    if clean in (".", ".."):
        return None
    if os.path.isabs(clean):
        return None
    if ":" in clean:  # a Windows drive letter
        return None
    if Path(clean).name != clean:
        return None
    return clean


def is_excluded(path: str | Path) -> bool:
    """True when *path* points at an AGENTS.md-excluded location."""
    normalized = str(path).replace("\\", "/").strip().lower()
    return any(marker.lower() in normalized for marker in EXCLUDED_MARKERS)


__all__ = [
    "EXCLUDED_MARKERS",
    "is_excluded",
    "is_within",
    "project_roots",
    "safe_skill_name",
    "skill_source_roots",
]
