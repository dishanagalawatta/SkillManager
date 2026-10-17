"""Read-only bug detection MCP tools: QML errors, screenshot comparison, visual issues, UI scenarios."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from skill_manager.mcp.bridge import (
    capture_app_window_info as _bridge_capture_app_window_info,
    compare_screenshot as _bridge_compare_screenshot,
    detect_qml_errors as _bridge_detect_qml_errors,
    find_visual_issues as _bridge_find_visual_issues,
    run_ui_scenario as _bridge_run_ui_scenario,
)
from skill_manager.mcp.models import ToolResult, err, ok

# ---------------------------------------------------------------------------
# Tool schemas with annotations
# ---------------------------------------------------------------------------
TOOL_SCHEMAS: dict[str, dict[str, Any]] = {
    "sm_detect_qml_errors": {
        "description": "Collect recent QML/JavaScript error messages from the Qt diagnostic buffer. Read-only.",
        "annotations": {
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
        "inputSchema": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "default": 50,
                    "minimum": 1,
                    "maximum": 500,
                    "description": "Max number of errors to return.",
                }
            },
        },
    },
    "sm_compare_screenshot": {
        "description": "Compare a baseline screenshot against the current UI screenshot or a supplied current image. The baseline may be provided as base64 PNG (baseline_b64) or by name (baseline_name) resolving to .agents/screenshots/<name>.png. The current image defaults to a capture of the live GUI, or a headless offscreen render when no GUI is running. Returns a structural similarity score, perceptual hash similarity, and diff pixel count.",
        "annotations": {
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
        "inputSchema": {
            "type": "object",
            "properties": {
                "baseline_b64": {
                    "type": "string",
                    "description": "Base64-encoded PNG of the baseline image (optional if baseline_name is given).",
                },
                "baseline_name": {
                    "type": "string",
                    "description": "Name of a baseline PNG stored in .agents/screenshots/<name>.png (optional if baseline_b64 is given).",
                },
                "current_b64": {
                    "type": ["string", "null"],
                    "default": None,
                    "description": "Base64-encoded PNG of the current image; null = capture live GUI.",
                },
                "threshold": {
                    "type": "number",
                    "default": 0.95,
                    "minimum": 0,
                    "maximum": 1,
                    "description": "Similarity threshold (0-1) for pass/fail.",
                },
            },
            "required": [],
        },
    },
    "sm_find_visual_issues": {
        "description": (
            "Scan a UI image for common visual issues: content clipped at the edges, insufficient "
            "contrast, overlapping elements. Pass image_b64 to analyse a specific capture, or omit "
            "it to analyse the current app window (live GUI or headless offscreen render). Read-only."
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
                "image_b64": {
                    "type": "string",
                    "description": (
                        "Base64-encoded PNG to inspect. Omit to capture the current app window "
                        "(headless --mcp renders Main.qml offscreen)."
                    ),
                },
                "check_clipping": {
                    "type": "boolean",
                    "default": True,
                    "description": "Check for text/UI clipping at edges.",
                },
                "check_contrast": {
                    "type": "boolean",
                    "default": True,
                    "description": "Check for insufficient color contrast.",
                },
                "check_overlap": {
                    "type": "boolean",
                    "default": True,
                    "description": "Check for overlapping UI elements.",
                },
            },
            "required": [],
        },
    },
    "sm_run_ui_scenario": {
        "description": (
            "Execute a predefined UI navigation scenario (navigate_library / navigate_quickcopy / "
            "navigate_updates / navigate_settings / full_tour) and verify each step took effect. "
            "In headless --mcp mode the offscreen window is navigated in-process; otherwise the "
            "live GUI acknowledges the navigation."
        ),
        "annotations": {
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
        "inputSchema": {
            "type": "object",
            "properties": {
                "scenario": {
                    "type": "string",
                    "enum": [
                        "navigate_library",
                        "navigate_quickcopy",
                        "navigate_updates",
                        "navigate_settings",
                        "full_tour",
                    ],
                    "description": "Scenario to run.",
                },
                "params": {
                    "type": ["object", "null"],
                    "default": None,
                    "description": "Optional scenario-specific parameters.",
                },
            },
            "required": ["scenario"],
        },
    },
}


# ---------------------------------------------------------------------------
# Tool handlers (return ToolResult)
# ---------------------------------------------------------------------------
def _handle_detect_qml_errors(args: dict[str, Any]) -> ToolResult:
    try:
        limit = int(args.get("limit", 50))
        result = _bridge_detect_qml_errors(limit=limit)
        if result.get("ok"):
            return ok("sm_detect_qml_errors", result)
        return err("sm_detect_qml_errors", result.get("error", "failed to detect QML errors"))
    except Exception as exc:  # noqa: BLE001
        return err("sm_detect_qml_errors", str(exc))


def _handle_compare_screenshot(args: dict[str, Any]) -> ToolResult:
    try:
        baseline_b64 = args.get("baseline_b64")
        baseline_name = args.get("baseline_name")
        current_b64 = args.get("current_b64")
        threshold = float(args.get("threshold", 0.95))
        result = _bridge_compare_screenshot(
            baseline_b64=baseline_b64 or "",
            baseline_name=baseline_name,
            current_b64=current_b64,
            threshold=threshold,
        )
        if result.get("ok"):
            return ok("sm_compare_screenshot", result)
        return err("sm_compare_screenshot", result.get("error", "failed to compare screenshots"))
    except Exception as exc:  # noqa: BLE001
        return err("sm_compare_screenshot", str(exc))


def _handle_find_visual_issues(args: dict[str, Any]) -> ToolResult:
    try:
        image_b64 = str(args.get("image_b64") or "")
        source = "provided"
        if not image_b64:
            capture = _bridge_capture_app_window_info()
            image_b64 = str(capture.get("image_b64") or "")
            source = str(capture.get("source") or "capture")
            if not image_b64:
                return err(
                    "sm_find_visual_issues",
                    capture.get("error") or "no image: capture failed and no image_b64 given",
                )
        check_clipping = bool(args.get("check_clipping", True))
        check_contrast = bool(args.get("check_contrast", True))
        check_overlap = bool(args.get("check_overlap", True))
        result = _bridge_find_visual_issues(
            image_b64=image_b64,
            check_clipping=check_clipping,
            check_contrast=check_contrast,
            check_overlap=check_overlap,
        )
        if result.get("ok"):
            result["source"] = source
            return ok("sm_find_visual_issues", result)
        return err("sm_find_visual_issues", result.get("error", "failed to find visual issues"))
    except Exception as exc:  # noqa: BLE001
        return err("sm_find_visual_issues", str(exc))


def _handle_run_ui_scenario(args: dict[str, Any]) -> ToolResult:
    try:
        scenario = str(args["scenario"])
        params = args.get("params")
        result = _bridge_run_ui_scenario(scenario=scenario, params=params)
        if result.get("ok"):
            return ok("sm_run_ui_scenario", result)
        return err("sm_run_ui_scenario", result.get("error", "failed to run UI scenario"))
    except Exception as exc:  # noqa: BLE001
        return err("sm_run_ui_scenario", str(exc))


# ---------------------------------------------------------------------------
# Dispatch table
# ---------------------------------------------------------------------------
_HANDLERS: dict[str, Callable[[dict[str, Any]], ToolResult]] = {
    "sm_detect_qml_errors": _handle_detect_qml_errors,
    "sm_compare_screenshot": _handle_compare_screenshot,
    "sm_find_visual_issues": _handle_find_visual_issues,
    "sm_run_ui_scenario": _handle_run_ui_scenario,
}


def get_handlers(_allow_write: bool = False) -> dict[str, Callable[..., Any]]:
    return dict(_HANDLERS)


__all__ = ["TOOL_SCHEMAS", "get_handlers"]
