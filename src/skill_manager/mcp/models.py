"""The result envelope shared by every SkillManager MCP tool.

Each tool module declares its own JSON schema in ``TOOL_SCHEMAS`` and
returns a :class:`ToolResult`; the server turns that into the MCP
``CallToolResult``.  The module deliberately has no PySide6 dependency, so
it can be imported in any environment (including a headless test runner)
without a Qt application instance.

Earlier revisions of this file also carried a Pydantic model per request and
response shape.  They were never used: the tool modules validate their
arguments against the hand-written schemas in ``TOOL_SCHEMAS`` and project
their results into plain dicts, so the models only duplicated the wire
contract without enforcing it.  They were removed rather than left to rot.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class ToolResult(BaseModel):
    """Uniform return envelope for every MCP tool call."""

    ok: bool
    tool: str
    data: dict[str, Any] | None = None
    error: str | None = None


def ok(tool: str, data: dict[str, Any] | None = None) -> ToolResult:
    """Build a successful ``ToolResult``."""
    return ToolResult(ok=True, tool=tool, data=data)


def err(tool: str, error: str) -> ToolResult:
    """Build a failed ``ToolResult``."""
    return ToolResult(ok=False, tool=tool, error=error)


def tool_annotations(
    *,
    read_only_hint: bool = True,
    destructive_hint: bool = True,
    idempotent_hint: bool = False,
    open_world_hint: bool = True,
) -> dict[str, bool]:
    """Build a standard tool annotations dict for MCP ``Tool`` objects.

    Annotations are hints that help clients understand tool behaviour:
    - ``readOnlyHint``: tool does not modify its environment.
    - ``destructiveHint``: tool may perform destructive updates.
    - ``idempotentHint``: repeated calls with same args have no additional effect.
    - ``openWorldHint``: tool interacts with external entities.
    """
    return {
        "readOnlyHint": read_only_hint,
        "destructiveHint": destructive_hint,
        "idempotentHint": idempotent_hint,
        "openWorldHint": open_world_hint,
    }


__all__ = ["ToolResult", "err", "ok", "tool_annotations"]
