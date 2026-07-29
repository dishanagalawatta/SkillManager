"""Write-capable MCP tools for the SkillManager MCP server (guarded).

This module registers mutating MCP tools (``sm_create_skill``, ``sm_update_skill``,
``sm_delete_skill``, ``sm_deploy``). They are intentionally gated behind an
``allow_write`` capability passed in at server startup.

Security model:
* Write tools are ONLY active when started with ``--mcp-allow-write``.
* AGENTS.md exclusions are enforced: we never mutate paths matching
  ``TODO.md``, ``.agents/commands/`` or ``.agents/skills/``.
* Every write attempt is recorded via ``capture_event("mcp_write_attempt", ...)``.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from skill_manager.core.analytics import capture_event
from skill_manager.mcp.bridge import create_skill, delete_skill, deploy, update_skill
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
    "sm_create_skill": {
        "description": "Create a new skill folder with SKILL.md. Gated by write mode; refuses AGENTS.md-excluded paths.",
        "annotations": {
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": False,
            "openWorldHint": False,
        },
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Name/folder of the skill to create.",
                },
                "content": {
                    "type": "string",
                    "description": "SKILL.md file content (frontmatter + body).",
                },
                "source_path": {
                    "type": "string",
                    "description": "Target parent source directory; empty = default source.",
                    "default": "",
                },
                "description": {
                    "type": "string",
                    "description": "Optional skill summary.",
                    "default": "",
                },
                "category": {
                    "type": "string",
                    "description": "Optional category.",
                    "default": "",
                },
            },
            "required": ["name", "content"],
        },
    },
    "sm_update_skill": {
        "description": "Update content or metadata of an existing skill's SKILL.md. Gated by write mode.",
        "annotations": {
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
        "inputSchema": {
            "type": "object",
            "properties": {
                "skill_id": {
                    "type": "string",
                    "description": "Skill name or local_path to update.",
                },
                "content": {
                    "type": "string",
                    "description": "Updated SKILL.md content.",
                    "default": "",
                },
                "description": {
                    "type": "string",
                    "description": "Updated summary.",
                    "default": "",
                },
                "category": {
                    "type": "string",
                    "description": "Updated category.",
                    "default": "",
                },
            },
            "required": ["skill_id"],
        },
    },
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
        "description": "Deploy a skill/package to a target project directory. Gated by write mode.",
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
                    "description": "Deployment target (project label or project directory path).",
                },
            },
            "required": ["skill_id", "target"],
        },
    },
}


# ---------------------------------------------------------------------------
# Per-tool handlers (return ToolResult)
# ---------------------------------------------------------------------------
def _handle_create_skill(args: dict[str, Any], allow_write: bool) -> ToolResult:
    name: str = str(args.get("name", ""))
    content: str = str(args.get("content", ""))
    source_path: str = str(args.get("source_path", ""))
    description: str = str(args.get("description", ""))
    category: str = str(args.get("category", ""))

    capture_event(
        "mcp_write_attempt",
        {"tool": "sm_create_skill", "allowed": allow_write, "name": name},
    )

    if not allow_write:
        return err("sm_create_skill", WRITE_DISABLED_ERROR)

    if _is_excluded(name) or (source_path and _is_excluded(source_path)):
        return err("sm_create_skill", "refused: target resolves under an AGENTS.md-excluded path.")

    try:
        result = create_skill(
            name=name,
            content=content,
            source_path=source_path,
            description=description,
            category=category,
        )
        return ok("sm_create_skill", result)
    except Exception as exc:  # noqa: BLE001
        return err("sm_create_skill", str(exc))


def _handle_update_skill(args: dict[str, Any], allow_write: bool) -> ToolResult:
    skill_id: str = str(args.get("skill_id", ""))
    content: str = str(args.get("content", ""))
    description: str = str(args.get("description", ""))
    category: str = str(args.get("category", ""))

    capture_event(
        "mcp_write_attempt",
        {"tool": "sm_update_skill", "allowed": allow_write, "skill_id": skill_id},
    )

    if not allow_write:
        return err("sm_update_skill", WRITE_DISABLED_ERROR)

    if _is_excluded(skill_id):
        return err("sm_update_skill", "refused: target resolves under an AGENTS.md-excluded path.")

    try:
        result = update_skill(
            skill_id=skill_id,
            content=content,
            description=description,
            category=category,
        )
        return ok("sm_update_skill", result)
    except Exception as exc:  # noqa: BLE001
        return err("sm_update_skill", str(exc))


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
    except (ValueError, RuntimeError) as exc:
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
        return ok("sm_deploy", result)
    except ValueError as exc:
        return err("sm_deploy", str(exc))
    except Exception as exc:  # noqa: BLE001
        return err("sm_deploy", str(exc))


# ---------------------------------------------------------------------------
# Dispatch table
# ---------------------------------------------------------------------------
def _bind_handlers(allow_write: bool) -> dict[str, Callable[[dict[str, Any]], ToolResult]]:
    from functools import partial

    return {
        "sm_create_skill": partial(_handle_create_skill, allow_write=allow_write),
        "sm_update_skill": partial(_handle_update_skill, allow_write=allow_write),
        "sm_delete_skill": partial(_handle_delete_skill, allow_write=allow_write),
        "sm_deploy": partial(_handle_deploy, allow_write=allow_write),
    }


def get_handlers(allow_write: bool = False) -> dict[str, Callable[..., Any]]:
    return dict(_bind_handlers(allow_write))


__all__ = ["TOOL_SCHEMAS", "get_handlers"]
