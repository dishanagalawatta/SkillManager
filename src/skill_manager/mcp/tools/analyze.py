"""MCP tool registration for SkillManager analysis/read-only tools.

This module wires the low-level ``mcp.server.Server`` API to the headless
bridge (``skill_manager.mcp.bridge``). It exposes four read-only tools:

* ``sm_list_skills``   — enumerate skills known to the library model
* ``sm_list_sources``  — list configured skill source directories
* ``sm_list_projects`` — list configured project directories
* ``sm_static_analyze`` — grep the repository for a pattern (respecting .gitignore)

Every handler is defensive: any exception is captured into a ``ToolResult``
with ``ok=False`` rather than propagating to the MCP transport. Each call is
recorded via ``capture_event("mcp_tool_call", ...)`` for analytics.

Server API pattern: low-level ``mcp.server.Server`` with the
``@server.list_tools`` / ``@server.call_tool`` decorators (NOT FastMCP). This
is the canonical style for the SkillManager MCP server; other tool modules in
this package must register via the same ``register_*_tools(server)`` entry
point so ``server.py`` can compose them onto a single ``Server`` instance.
"""

from __future__ import annotations

import contextlib
from collections.abc import Callable, Coroutine
from typing import Any

from mcp.server import Server
from mcp.types import TextContent, Tool

from skill_manager.core.analytics import capture_event
from skill_manager.mcp.bridge import (
    list_projects,
    list_skills,
    list_sources,
    static_analyze,
)
from skill_manager.mcp.models import ToolResult

# ---------------------------------------------------------------------------
# Result helpers
# ---------------------------------------------------------------------------


def _ok(tool: str, data: dict[str, Any]) -> ToolResult:
    """Build a successful ``ToolResult`` envelope."""
    return ToolResult(ok=True, tool=tool, data=data, error=None)


def _err(tool: str, error: str) -> ToolResult:
    """Build a failed ``ToolResult`` envelope."""
    return ToolResult(ok=False, tool=tool, data=None, error=error)


def _emit(tool: str, args: dict[str, Any]) -> None:
    """Record a tool invocation via analytics (never raises)."""
    with contextlib.suppress(Exception):  # analytics must never break a tool call
        capture_event("mcp_tool_call", {"tool": tool, "args": args})


def _to_content(result: ToolResult) -> list[TextContent]:
    """Serialize a ``ToolResult`` to MCP text content blocks."""
    return [TextContent(type="text", text=result.model_dump_json())]


# ---------------------------------------------------------------------------
# Tool handlers
# ---------------------------------------------------------------------------


async def _handle_list_skills(args: dict[str, Any]) -> list[TextContent]:
    """Handle ``sm_list_skills``: enumerate skills from the library model."""
    tool = "sm_list_skills"
    include_commands: bool = bool(args.get("include_commands", True))
    project_label: str = str(args.get("project_label", ""))
    _emit(tool, {"include_commands": include_commands, "project_label": project_label})
    try:
        skills = list_skills(include_commands=include_commands, project_label=project_label)
        return _to_content(_ok(tool, {"skills": skills}))
    except Exception as exc:  # noqa: BLE001 - degrade to a ToolResult error
        return _to_content(_err(tool, str(exc)))


async def _handle_list_sources(_args: dict[str, Any]) -> list[TextContent]:
    """Handle ``sm_list_sources``: list configured skill source directories."""
    tool = "sm_list_sources"
    _emit(tool, {})
    try:
        sources = list_sources()
        return _to_content(_ok(tool, {"sources": sources}))
    except Exception as exc:  # noqa: BLE001
        return _to_content(_err(tool, str(exc)))


async def _handle_list_projects(_args: dict[str, Any]) -> list[TextContent]:
    """Handle ``sm_list_projects``: list configured project directories."""
    tool = "sm_list_projects"
    _emit(tool, {})
    try:
        projects = list_projects()
        return _to_content(_ok(tool, {"projects": projects}))
    except Exception as exc:  # noqa: BLE001
        return _to_content(_err(tool, str(exc)))


async def _handle_static_analyze(args: dict[str, Any]) -> list[TextContent]:
    """Handle ``sm_static_analyze``: grep the repo for a pattern."""
    tool = "sm_static_analyze"
    pattern: str = str(args.get("pattern", ""))
    path: str = str(args.get("path", "src"))
    _emit(tool, {"pattern": pattern, "path": path})
    if not pattern:
        return _to_content(_err(tool, "argument 'pattern' is required and must be non-empty"))
    try:
        matches = static_analyze(pattern=pattern, path=path)
        return _to_content(_ok(tool, {"matches": matches}))
    except Exception as exc:  # noqa: BLE001
        return _to_content(_err(tool, str(exc)))


# ---------------------------------------------------------------------------
# Tool registry
# ---------------------------------------------------------------------------
_TOOLS: list[Tool] = [
    Tool(
        name="sm_list_skills",
        description=(
            "List skills known to the SkillManager library model. Returns a list "
            "of skill summaries (name, local_path, category, project_label, flags, "
            "client, risk, source). Optionally filter out command-type skills or "
            "restrict to a single project label."
        ),
        inputSchema={
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
    ),
    Tool(
        name="sm_list_sources",
        description=(
            "List the configured skill source directories that SkillManager reads skills from."
        ),
        inputSchema={
            "type": "object",
            "properties": {},
            "required": [],
        },
    ),
    Tool(
        name="sm_list_projects",
        description=(
            "List the configured project directories that SkillManager can deploy "
            "skills to or associate skills with."
        ),
        inputSchema={
            "type": "object",
            "properties": {},
            "required": [],
        },
    ),
    Tool(
        name="sm_static_analyze",
        description=(
            "Grep the repository for a regular expression, respecting .gitignore. "
            "Returns a list of matches with file, line, and text. The 'pattern' "
            "argument is required; 'path' selects the search root (default 'src')."
        ),
        inputSchema={
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
    ),
]

# Map tool name -> async handler.
_HANDLERS: dict[str, Callable[[dict[str, Any]], Coroutine[Any, Any, list[TextContent]]]] = {
    "sm_list_skills": _handle_list_skills,
    "sm_list_sources": _handle_list_sources,
    "sm_list_projects": _handle_list_projects,
    "sm_static_analyze": _handle_static_analyze,
}

# Public schema surface (name -> {description, inputSchema}) for server.py.
TOOL_SCHEMAS: dict[str, dict[str, Any]] = {
    tool.name: {"description": tool.description, "inputSchema": tool.inputSchema} for tool in _TOOLS
}


def get_handlers(_allow_write: bool = False) -> dict[str, Callable[..., Any]]:
    """Return the analyze tool dispatch table (name -> handler).

    The ``_allow_write`` parameter is accepted for a uniform module interface
    but is unused: analyze tools are read-only.
    """
    return dict(_HANDLERS)


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


def register_analyze_tools(_server: Server[Any]) -> None:
    """Register the analysis/read-only tools onto a low-level MCP ``Server``.

    .. deprecated::
        Tool registration now happens centrally in ``server.py`` via a single
        ``list_tools`` / ``call_tool`` pair. This function is retained as a
        no-op so existing importers keep working; it MUST NOT decorate any
        ``call_tool`` handler (the SDK keeps only one such slot).
    """
    return


__all__ = ["register_analyze_tools", "TOOL_SCHEMAS", "get_handlers"]
