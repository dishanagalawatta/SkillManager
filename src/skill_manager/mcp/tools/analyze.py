"""MCP tool registration for SkillManager analysis/read-only tools.

This module exposes four read-only tools:

* ``sm_list_skills``   — enumerate skills known to the library model
* ``sm_list_sources``  — list configured skill source directories
* ``sm_list_projects`` — list configured project directories
* ``sm_static_analyze`` — grep the repository for a pattern (respecting .gitignore)

Every handler is defensive: any exception is captured into a ``ToolResult``
with ``ok=False`` rather than propagating to the MCP transport.
"""

from __future__ import annotations

import contextlib
from collections.abc import Callable, Coroutine
from typing import Any

from skill_manager.core.analytics import capture_event
from skill_manager.mcp.bridge import (
    list_projects,
    list_skills,
    list_sources,
    static_analyze,
)
from skill_manager.mcp.models import ToolResult, err, ok


def _emit(tool: str, args: dict[str, Any]) -> None:
    with contextlib.suppress(Exception):
        capture_event("mcp_tool_call", {"tool": tool, "args": args})


# ---------------------------------------------------------------------------
# Tool schemas with annotations
# ---------------------------------------------------------------------------
_TOOL_META: list[dict[str, Any]] = [
    {
        "name": "sm_list_skills",
        "description": (
            "List skills known to the SkillManager library model. Returns a list "
            "of skill summaries (name, local_path, category, project_label, flags, "
            "client, risk, source). Optionally filter out command-type skills or "
            "restrict to a single project label."
        ),
        "annotations": {
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
        "inputSchema": {
            "type": "object",
            "properties": {
                "include_commands": {
                    "type": "boolean",
                    "description": "Include command-type skills in the listing.",
                    "default": True,
                },
                "project_label": {
                    "type": "string",
                    "description": "Restrict to a single project label; empty = all projects.",
                    "default": "",
                },
            },
            "required": [],
        },
    },
    {
        "name": "sm_list_sources",
        "description": (
            "List the configured skill source directories that SkillManager reads skills from."
        ),
        "annotations": {
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
        "inputSchema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "sm_list_projects",
        "description": (
            "List the configured project directories that SkillManager can deploy "
            "skills to or associate skills with."
        ),
        "annotations": {
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
        "inputSchema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "sm_static_analyze",
        "description": (
            "Grep the repository for a regular expression, respecting .gitignore. "
            "Returns a list of matches with file, line, and text. The 'pattern' "
            "argument is required; 'path' selects the search root (default 'src')."
        ),
        "annotations": {
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
        "inputSchema": {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "Regular expression to search for (required).",
                },
                "path": {
                    "type": "string",
                    "description": "Root directory to search within.",
                    "default": "src",
                },
            },
            "required": ["pattern"],
        },
    },
]

# Public schema surface (name -> {description, inputSchema, annotations}) for server.py.
TOOL_SCHEMAS: dict[str, dict[str, Any]] = {
    m["name"]: {
        "description": m["description"],
        "inputSchema": m["inputSchema"],
        "annotations": m["annotations"],
    }
    for m in _TOOL_META
}


# ---------------------------------------------------------------------------
# Tool handlers (return ToolResult)
# ---------------------------------------------------------------------------
async def _handle_list_skills(args: dict[str, Any]) -> ToolResult:
    tool = "sm_list_skills"
    include_commands: bool = bool(args.get("include_commands", True))
    project_label: str = str(args.get("project_label", ""))
    _emit(tool, {"include_commands": include_commands, "project_label": project_label})
    try:
        skills = list_skills(include_commands=include_commands, project_label=project_label)
        return ok(tool, {"skills": skills})
    except Exception as exc:
        return err(tool, str(exc))


async def _handle_list_sources(_args: dict[str, Any]) -> ToolResult:
    tool = "sm_list_sources"
    _emit(tool, {})
    try:
        sources = list_sources()
        return ok(tool, {"sources": sources})
    except Exception as exc:
        return err(tool, str(exc))


async def _handle_list_projects(_args: dict[str, Any]) -> ToolResult:
    tool = "sm_list_projects"
    _emit(tool, {})
    try:
        projects = list_projects()
        return ok(tool, {"projects": projects})
    except Exception as exc:
        return err(tool, str(exc))


async def _handle_static_analyze(args: dict[str, Any]) -> ToolResult:
    tool = "sm_static_analyze"
    pattern: str = str(args.get("pattern", ""))
    path: str = str(args.get("path", "src"))
    _emit(tool, {"pattern": pattern, "path": path})
    if not pattern:
        return err(tool, "argument 'pattern' is required and must be non-empty")
    try:
        matches = static_analyze(pattern=pattern, path=path)
        return ok(tool, {"matches": matches})
    except Exception as exc:
        return err(tool, str(exc))


# ---------------------------------------------------------------------------
# Public dispatch surface
# ---------------------------------------------------------------------------
_HANDLERS: dict[str, Callable[[dict[str, Any]], Coroutine[Any, Any, ToolResult]]] = {
    "sm_list_skills": _handle_list_skills,
    "sm_list_sources": _handle_list_sources,
    "sm_list_projects": _handle_list_projects,
    "sm_static_analyze": _handle_static_analyze,
}


def get_handlers(_allow_write: bool = False) -> dict[str, Callable[..., Any]]:
    return dict(_HANDLERS)


__all__ = ["TOOL_SCHEMAS", "get_handlers"]
