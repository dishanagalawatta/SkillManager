"""MCP tool registration for SkillManager skill management tools (read-only).

This module exposes read-only skill management tools:

* ``sm_get_skill``     — retrieve full content and metadata of a single skill
* ``sm_search_skills`` — search skills by query across name, description, tags, content
* ``sm_sync_skills``   — re-scan skill sources and update the library model

Every handler is defensive: any exception is captured into a ``ToolResult``
with ``ok=False`` rather than propagating to the MCP transport.
"""

from __future__ import annotations

import contextlib
from collections.abc import Callable, Coroutine
from typing import Any

from skill_manager.core.analytics import capture_event
from skill_manager.mcp.bridge import (
    get_skill,
    search_skills,
    sync_skills,
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
        "name": "sm_get_skill",
        "description": (
            "Retrieve full details of a single skill by name, folder name, or local_path. "
            "Returns metadata, description, full SKILL.md content, and list of files in the skill folder."
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
                "skill_id": {
                    "type": "string",
                    "description": "Skill name, folder name, or local_path to retrieve.",
                },
            },
            "required": ["skill_id"],
        },
    },
    {
        "name": "sm_search_skills",
        "description": (
            "Search skills by query string matching name, category, description, tags, or content."
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
                "query": {
                    "type": "string",
                    "description": "Search query or phrase.",
                },
                "category": {
                    "type": "string",
                    "description": "Optional category filter.",
                    "default": "",
                },
                "project_label": {
                    "type": "string",
                    "description": "Optional project label filter.",
                    "default": "",
                },
                "include_commands": {
                    "type": "boolean",
                    "description": "Include command-type skills in search results.",
                    "default": True,
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of results to return.",
                    "default": 50,
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "sm_sync_skills",
        "description": (
            "Re-scan skill source directories and target projects, refreshing the in-memory library model."
        ),
        "annotations": {
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": False,
            "openWorldHint": False,
        },
        "inputSchema": {
            "type": "object",
            "properties": {
                "force_full_scan": {
                    "type": "boolean",
                    "description": "Force deep re-scan ignoring cached fingerprints.",
                    "default": False,
                },
            },
            "required": [],
        },
    },
]

# Public schema surface for server.py
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
async def _handle_get_skill(args: dict[str, Any]) -> ToolResult:
    tool = "sm_get_skill"
    skill_id: str = str(args.get("skill_id", ""))
    _emit(tool, {"skill_id": skill_id})
    if not skill_id:
        return err(tool, "argument 'skill_id' is required and must be non-empty")
    try:
        res = get_skill(skill_id)
        if not res.get("found"):
            return err(tool, f"skill {skill_id!r} not found")
        return ok(tool, res)
    except Exception as exc:  # noqa: BLE001
        return err(tool, str(exc))


async def _handle_search_skills(args: dict[str, Any]) -> ToolResult:
    tool = "sm_search_skills"
    query: str = str(args.get("query", ""))
    category: str = str(args.get("category", ""))
    project_label: str = str(args.get("project_label", ""))
    include_commands: bool = bool(args.get("include_commands", True))
    limit: int = int(args.get("limit", 50))

    _emit(tool, {"query": query, "category": category, "project_label": project_label})
    try:
        skills = search_skills(
            query=query,
            category=category,
            project_label=project_label,
            include_commands=include_commands,
            limit=limit,
        )
        return ok(tool, {"count": len(skills), "skills": skills})
    except Exception as exc:  # noqa: BLE001
        return err(tool, str(exc))


async def _handle_sync_skills(args: dict[str, Any]) -> ToolResult:
    tool = "sm_sync_skills"
    force_full_scan: bool = bool(args.get("force_full_scan", False))
    _emit(tool, {"force_full_scan": force_full_scan})
    try:
        res = sync_skills(force_full_scan=force_full_scan)
        return ok(tool, res)
    except Exception as exc:  # noqa: BLE001
        return err(tool, str(exc))


# ---------------------------------------------------------------------------
# Public dispatch surface
# ---------------------------------------------------------------------------
_HANDLERS: dict[str, Callable[[dict[str, Any]], Coroutine[Any, Any, ToolResult]]] = {
    "sm_get_skill": _handle_get_skill,
    "sm_search_skills": _handle_search_skills,
    "sm_sync_skills": _handle_sync_skills,
}


def get_handlers(_allow_write: bool = False) -> dict[str, Callable[..., Any]]:
    return dict(_HANDLERS)


__all__ = ["TOOL_SCHEMAS", "get_handlers"]
