"""Write-capable MCP tools for the SkillManager MCP server (guarded).

This module registers the *destructive* MCP tools (``sm_delete_skill``,
``sm_deploy``). They are intentionally gated behind an ``allow_write``
capability that the server passes in at registration time.

Security model (per project constraints):
* Write tools are ONLY active when the server was started with
  ``--mcp-allow-write``.
* AGENTS.md exclusions are enforced: we never operate on paths matching
  ``TODO.md``, ``.agents/commands/`` or ``.agents/skills/``.
* Every write attempt is recorded via ``capture_event("mcp_write_attempt", ...)``.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from skill_manager.core.analytics import capture_event
from skill_manager.mcp.bridge import delete_skill, deploy
from skill_manager.mcp.models import ToolResult, err, ok

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
WRITE_DISABLED_ERROR = "write mode disabled \u2014 restart with --mcp-allow-write"

# AGENTS.md exclusions \u2014 never operate on these paths.
_EXCLUDED_MARKERS: tuple[str, ...] = (
    ".agents/skills",
    ".agents/commands",
    "TODO.md",
)


def _is_excluded(identifier: str) -> bool:
    normalized = identifier.replace("\\", "/").strip().lower()
    return any(marker.lower() in normalized for marker in _EXCLUDED_MARKERS)


# ---------------------------------------------------------------------------
# Tool schemas with annotations
# ---------------------------------------------------------------------------
TOOL_SCHEMAS: dict[str, dict[str, Any]] = {
    "sm_delete_skill": {
        "description": "Delete a skill by name or local_path. Gated by write mode; refuses AGENTS.md-excluded paths (TODO.md, .agents/commands, .agents/skills).",
        "annotations": {
            "readOnlyHint": False,
            "destructiveHint": True,
            "idempotentHint": True,
            "openWorldHint": False,
        },
        "inputSchema": {
            "type": "object",
            "properties": {
                "skill_id": {
                    "type": "string",
                    "description": "Skill name or local_path to delete.",
                }
            },
            "required": ["skill_id"],
        },
    },
    "sm_deploy": {
        "description": "Deploy a skill/package to a target. Gated by write mode; currently not implemented in the app (returns a clear error).",
        "annotations": {
            "readOnlyHint": False,
            "destructiveHint": True,
            "idempotentHint": True,
            "openWorldHint": False,
        },
        "inputSchema": {
            "type": "object",
            "properties": {
                "skill_id": {
                    "type": "string",
                    "description": "Skill name or local_path to deploy.",
                },
                "target": {
                    "type": "string",
                    "description": "Deployment target (project label or path).",
                },
            },
            "required": ["skill_id", "target"],
        },
    },
}


# ---------------------------------------------------------------------------
# Per-tool handlers (return ToolResult)
# ---------------------------------------------------------------------------
def _handle_delete_skill(args: dict[str, Any], allow_write: bool) -> ToolResult:
    skill_id: str = args.get("skill_id", "")

    capture_event(
        "mcp_write_attempt",
        {"tool": "sm_delete_skill", "allowed": allow_write, "skill_id": skill_id},
    )

    if not allow_write:
        return err("sm_delete_skill", WRITE_DISABLED_ERROR)

    if _is_excluded(skill_id):
        return err(
            "sm_delete_skill", "refused: skill_id resolves under an AGENTS.md-excluded path."
        )

    try:
        result = delete_skill(skill_id)
    except (ValueError, NotImplementedError) as exc:
        return err("sm_delete_skill", str(exc))

    resolved_path = result.get("resolved_path") if isinstance(result, dict) else None
    if isinstance(resolved_path, str) and _is_excluded(resolved_path):
        return err(
            "sm_delete_skill", "refused: resolved path is under an AGENTS.md-excluded directory."
        )

    return ok("sm_delete_skill", result)


def _handle_deploy(args: dict[str, Any], allow_write: bool) -> ToolResult:
    skill_id: str = args.get("skill_id", "")
    target: str = args.get("target", "")

    capture_event(
        "mcp_write_attempt",
        {"tool": "sm_deploy", "allowed": allow_write, "skill_id": skill_id, "target": target},
    )

    if not allow_write:
        return err("sm_deploy", WRITE_DISABLED_ERROR)

    if _is_excluded(skill_id):
        return err("sm_deploy", "refused: skill_id resolves under an AGENTS.md-excluded path.")

    try:
        result = deploy(skill_id, target)
    except NotImplementedError:
        return err("sm_deploy", "deploy not yet implemented in app")
    except ValueError as exc:
        return err("sm_deploy", str(exc))

    return ok("sm_deploy", result)


# ---------------------------------------------------------------------------
# Dispatch table
# ---------------------------------------------------------------------------
def _bind_handlers(allow_write: bool) -> dict[str, Callable[[dict[str, Any]], ToolResult]]:
    from functools import partial

    return {
        "sm_delete_skill": partial(_handle_delete_skill, allow_write=allow_write),
        "sm_deploy": partial(_handle_deploy, allow_write=allow_write),
    }


def get_handlers(allow_write: bool = False) -> dict[str, Callable[..., Any]]:
    return dict(_bind_handlers(allow_write))


__all__ = ["TOOL_SCHEMAS", "get_handlers"]
