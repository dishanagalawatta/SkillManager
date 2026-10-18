"""Read-only ``sm_accessibility_audit`` MCP tool for QML accessibility auditing.

Traverses the QML object tree and flags accessibility issues: missing roles,
missing accessible names, unlabeled buttons, etc. Read-only; never mutates app
state. Degrades gracefully when the QML engine is not available.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from pydantic import BaseModel, Field

from skill_manager.core.analytics import capture_mcp_tool_call
from skill_manager.mcp.bridge import audit_accessibility as _bridge_audit_accessibility
from skill_manager.mcp.models import ToolResult, err, ok


# ---------------------------------------------------------------------------
# Request model
# ---------------------------------------------------------------------------
class _AccessibilityAuditArgs(BaseModel):
    max_depth: int = Field(default=10, ge=1, le=30, description="Maximum QML tree depth to audit.")


# ---------------------------------------------------------------------------
# Tool schema with annotations
# ---------------------------------------------------------------------------
TOOL_SCHEMAS: dict[str, dict[str, Any]] = {
    "sm_accessibility_audit": {
        "description": (
            "Audit the UI for accessibility issues by walking Qt's accessible tree "
            "(what assistive technology sees): interactive controls with no "
            "accessible name are reported as unlabeled_button / missing_name, with "
            "the node path and window rect so they can be located. Read-only. Works "
            "in headless --mcp mode by rendering Main.qml offscreen on demand; no "
            "running GUI required."
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
                "max_depth": {
                    "type": "integer",
                    "default": 10,
                    "minimum": 1,
                    "maximum": 30,
                    "description": "Maximum QML tree depth to audit (1-30).",
                }
            },
            "required": [],
        },
    },
}


# ---------------------------------------------------------------------------
# Tool handler
# ---------------------------------------------------------------------------
def _handle_accessibility_audit(args: dict[str, Any]) -> ToolResult:
    try:
        parsed = _AccessibilityAuditArgs(**args)
        capture_mcp_tool_call(
            "mcp_tool_call",
            "sm_accessibility_audit",
            {"max_depth": parsed.max_depth},
        )
        result = _bridge_audit_accessibility(max_depth=parsed.max_depth)
        if result.get("ok"):
            return ok("sm_accessibility_audit", result)
        return err(
            "sm_accessibility_audit",
            result.get("error", "accessibility audit failed"),
        )
    except Exception as exc:  # noqa: BLE001
        return err("sm_accessibility_audit", str(exc))


# ---------------------------------------------------------------------------
# Public dispatch surface
# ---------------------------------------------------------------------------
def get_handlers(_allow_write: bool = False) -> dict[str, Callable[..., Any]]:
    def _dispatch(args: dict[str, Any]) -> ToolResult:
        return _handle_accessibility_audit(args)

    return {"sm_accessibility_audit": _dispatch}


__all__ = ["TOOL_SCHEMAS", "get_handlers"]
