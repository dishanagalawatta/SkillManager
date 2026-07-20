"""Write-capable MCP tools for the SkillManager MCP server (guarded).

This module registers the *destructive* MCP tools (``sm_delete_skill``,
``sm_deploy``). They are intentionally gated behind an ``allow_write``
capability that the server passes in at registration time — the bridge layer
(``skill_manager.mcp.bridge``) has no knowledge of that flag, so the gate
lives here.

Security model (per project constraints):
* Write tools are ONLY active when the server was started with
  ``--mcp-allow-write``. When ``allow_write`` is ``False`` every tool
  immediately returns ``ToolResult(ok=False, error="write mode disabled
  — restart with --mcp-allow-write")``.
* AGENTS.md exclusions are enforced: we never operate on paths matching
  ``TODO.md``, ``.agents/commands/`` or ``.agents/skills/``. The bridge
  resolves ``skill_id`` against the model (so it is already safe), but we
  add a defensive pre-check on the raw ``skill_id`` and a post-check on the
  resolved path returned by the bridge.
* Every write attempt is recorded via ``capture_event("mcp_write_attempt", ...)``.

The module is dependency-light: it only imports the bridge, the models, and
the analytics hook. It does NOT import PySide6 directly.

Server API pattern
------------------
``register_write_tools`` decorates the passed ``mcp.server.Server`` instance
with ``@server.list_tools()`` and ``@server.call_tool()`` — mirroring the
other tool modules (build.py, analyze.py, monitor.py, debug.py) so the server
entrypoint can call each ``register_*_tools(server, ...)`` uniformly.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from skill_manager.core.analytics import capture_event
from skill_manager.mcp.bridge import delete_skill, deploy
from skill_manager.mcp.models import ToolResult

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
WRITE_DISABLED_ERROR = "write mode disabled — restart with --mcp-allow-write"

# AGENTS.md exclusions — never operate on these paths.
_EXCLUDED_MARKERS: tuple[str, ...] = (
    ".agents/skills",
    ".agents/commands",
    "TODO.md",
)


def _is_excluded(identifier: str) -> bool:
    """Return True if ``identifier`` falls under an AGENTS.md exclusion.

    The check is deliberately simple and defensive: it normalizes separators
    and tests the raw ``skill_id`` (which may be a name or a path) against
    the forbidden markers. We never resolve or guess — a match means refuse.
    """
    normalized = identifier.replace("\\", "/").strip().lower()
    return any(marker.lower() in normalized for marker in _EXCLUDED_MARKERS)


# ---------------------------------------------------------------------------
# Envelope helpers
# ---------------------------------------------------------------------------


def _ok(tool: str, data: dict[str, Any] | None) -> dict[str, Any]:
    """Build a successful ToolResult envelope as a plain dict."""
    return ToolResult(ok=True, tool=tool, data=data).model_dump()


def _err(tool: str, exc: Exception) -> dict[str, Any]:
    """Build a failed ToolResult envelope as a plain dict."""
    return ToolResult(ok=False, tool=tool, error=str(exc)).model_dump()


# ---------------------------------------------------------------------------
# Tool registry (name -> metadata + handler)
# ---------------------------------------------------------------------------
_TOOL_SCHEMAS: dict[str, dict[str, Any]] = {
    "sm_delete_skill": {
        "description": (
            "Delete a skill by name or local_path. Gated by write mode; "
            "refuses AGENTS.md-excluded paths (TODO.md, .agents/commands, "
            ".agents/skills)."
        ),
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
        "description": (
            "Deploy a skill/package to a target. Gated by write mode; "
            "currently not implemented in the app (returns a clear error)."
        ),
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
# Per-tool handlers (return ToolResult dicts)
# ---------------------------------------------------------------------------
#
# Handlers take ONLY ``args`` (matching the dispatch contract used by every
# other tool module: ``handler(args)``). The ``allow_write`` gate is closed
# over at registration time by ``register_write_tools`` via ``functools.partial``,
# so the dispatch table entries are plain ``(args) -> result`` callables.


def _handle_delete_skill(args: dict[str, Any], allow_write: bool) -> dict[str, Any]:
    """Delete a skill, gated by ``allow_write`` and AGENTS.md exclusions."""
    skill_id: str = args.get("skill_id", "")

    capture_event(
        "mcp_write_attempt",
        {"tool": "sm_delete_skill", "allowed": allow_write, "skill_id": skill_id},
    )

    if not allow_write:
        return _err(
            "sm_delete_skill",
            RuntimeError(WRITE_DISABLED_ERROR),
        )

    if _is_excluded(skill_id):
        return _err(
            "sm_delete_skill",
            RuntimeError("refused: skill_id resolves under an AGENTS.md-excluded path."),
        )

    try:
        result = delete_skill(skill_id)
    except (ValueError, NotImplementedError) as exc:
        return _err("sm_delete_skill", exc)

    # Post-call guard: the bridge resolved a path; refuse if it lands in an
    # excluded directory. Defensive belt-and-braces on top of the pre-check.
    resolved_path = result.get("resolved_path") if isinstance(result, dict) else None
    if isinstance(resolved_path, str) and _is_excluded(resolved_path):
        return _err(
            "sm_delete_skill",
            RuntimeError("refused: resolved path is under an AGENTS.md-excluded directory."),
        )

    return _ok("sm_delete_skill", result)


def _handle_deploy(args: dict[str, Any], allow_write: bool) -> dict[str, Any]:
    """Deploy a skill, gated by ``allow_write``.

    The bridge's ``deploy`` raises ``NotImplementedError`` (no deploy API
    exists yet); we catch it and translate to a clear ToolResult error.
    """
    skill_id: str = args.get("skill_id", "")
    target: str = args.get("target", "")

    capture_event(
        "mcp_write_attempt",
        {
            "tool": "sm_deploy",
            "allowed": allow_write,
            "skill_id": skill_id,
            "target": target,
        },
    )

    if not allow_write:
        return _err(
            "sm_deploy",
            RuntimeError(WRITE_DISABLED_ERROR),
        )

    if _is_excluded(skill_id):
        return _err(
            "sm_deploy",
            RuntimeError("refused: skill_id resolves under an AGENTS.md-excluded path."),
        )

    try:
        result = deploy(skill_id, target)
    except NotImplementedError:
        return _err("sm_deploy", RuntimeError("deploy not yet implemented in app"))
    except ValueError as exc:
        return _err("sm_deploy", exc)

    return _ok("sm_deploy", result)


# Dispatch table bound at registration time via ``_bind_handlers(allow_write)``.
# Each entry is ``(args) -> result`` so the server's call_tool dispatcher can
# invoke it uniformly with every other tool module.
def _bind_handlers(allow_write: bool) -> dict[str, Callable[[dict[str, Any]], dict[str, Any]]]:
    """Return the dispatch table with ``allow_write`` closed over."""
    from functools import partial

    return {
        "sm_delete_skill": partial(_handle_delete_skill, allow_write=allow_write),
        "sm_deploy": partial(_handle_deploy, allow_write=allow_write),
    }


# Public schema surface (name -> {description, inputSchema}) for server.py.
TOOL_SCHEMAS: dict[str, dict[str, Any]] = _TOOL_SCHEMAS


def get_handlers(allow_write: bool = False) -> dict[str, Callable[..., Any]]:
    """Return the write tool dispatch table with ``allow_write`` closed over."""
    return dict(_bind_handlers(allow_write))


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


def register_write_tools(_server: Any, allow_write: bool) -> None:  # noqa: ARG001
    """Register the guarded write MCP tools on ``server``.

    .. deprecated::
        Tool registration now happens centrally in ``server.py`` via a single
        ``list_tools`` / ``call_tool`` pair. This function is retained as a
        no-op so existing importers keep working; it MUST NOT decorate any
        ``call_tool`` handler (the SDK keeps only one such slot).
    """
    return


__all__ = ["register_write_tools", "TOOL_SCHEMAS", "get_handlers", "_bind_handlers"]
