"""Detect which skills a command body depends on.

Pure parsing — no filesystem mutation, no Qt. Used by the carry flow
(see copier.copy_commands_with_skill_carry) and by the QuickCopy
reference formatter.

Mirrors the regex/lookup used by
quick_copy.replace_skill_references_in_command but returns the match
set, not the substituted text.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

# Same pattern as quick_copy.replace_skill_references_in_command.
# Group 1: Codex  [$name](path) → name
# Whole match: /name  or  @path/to/name
REF_PATTERN = re.compile(
    r"\[\$([^\]]+)\]\([^)]+\)|"  # Codex: [$name](path)
    r"\/[a-zA-Z0-9_-]+|"  # Antigravity / OpenCode: /name
    r"@[a-zA-Z0-9_.-]+(?:/[a-zA-Z0-9_.-]+)*"  # Gemini CLI: @name or @path/name
)


def extract_skill_names(content: str) -> list[str]:
    """Return ordered, de-duped skill name candidates referenced in *content*.

    Handles all four client formats:

    * ``/name`` — Antigravity, OpenCode
    * ``@name`` — Gemini CLI (short)
    * ``@path/to/name`` — Gemini CLI (long)
    * ``[$name](path)`` — Codex

    Unknown names are returned as-is; the caller resolves them against
    ``all_skills``.
    """
    if not content:
        return []

    seen: set[str] = set()
    out: list[str] = []

    for m in REF_PATTERN.finditer(str(content)):
        token = m.group(0)
        name = ""

        if token.startswith("[$"):
            # Codex: [$name](path)
            name = m.group(1)
        elif token.startswith("/"):
            # Antigravity / OpenCode: /name
            name = token[1:]
        elif token.startswith("@"):
            # Gemini CLI: @name or @path/to/name
            parts = token.split("/")
            name = parts[-2] if token.endswith("/SKILL.md") and len(parts) >= 2 else parts[-1]
            name = name.lstrip("@")

        if name:
            key = name.lower()
            if key not in seen:
                seen.add(key)
                out.append(name)

    return out


def resolve_referenced_skills(
    content: str,
    all_skills: Iterable[dict],
) -> list[dict]:
    """Return the subset of *all_skills* referenced by *content*.

    Matches against both ``folder_name`` and ``name`` (case-insensitive).
    Commands and screenshots are excluded. Order is preserved; duplicates
    (by ``local_path``) are removed.
    """
    names = [n.lower() for n in extract_skill_names(content)]
    if not names:
        return []

    by_folder: dict[str, dict] = {}
    by_name: dict[str, dict] = {}
    for s in all_skills:
        if s.get("is_command") or s.get("is_screenshot"):
            continue
        folder = str(s.get("folder_name") or "").strip().lower()
        name = str(s.get("name") or "").strip().lower()
        if folder:
            by_folder[folder] = s
        if name:
            by_name[name] = s

    seen: set[str] = set()
    out: list[dict] = []
    for n in names:
        match = by_folder.get(n) or by_name.get(n)
        if match:
            lp = match.get("local_path")
            if lp and lp not in seen:
                seen.add(lp)
                out.append(match)
    return out
