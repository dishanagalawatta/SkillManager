"""Bug detection bridge functions: QML errors and UI scenario execution."""

from __future__ import annotations

from typing import Any

from ._controller import _controller_or_none
from ._ipc import send_navigation_command
from ._qml_headless import headless_qml_enabled
from ._state import get_diagnostics
from ._telemetry import _log_call


def detect_qml_errors(limit: int = 50) -> dict[str, Any]:
    """Collect recent QML/JavaScript error messages from the diagnostic buffer."""
    _log_call("detect_qml_errors")
    try:
        limit = max(1, min(int(limit), 500))
        events = get_diagnostics(limit=limit)
        errors: list[dict[str, Any]] = []
        for event in events:
            level = str(event.get("level", "")).upper()
            if level in ("ERROR", "CRITICAL", "FATAL"):
                errors.append(
                    {
                        "ts": str(event.get("ts", "")),
                        "level": str(event.get("level", "error")),
                        "msg": str(event.get("msg", "")),
                        "file": event.get("file"),
                        "line": event.get("line"),
                        "column": event.get("column"),
                    }
                )
        return {"ok": True, "count": len(errors), "errors": errors, "error": None}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "count": 0, "errors": [], "error": str(exc)}


# Named UI navigation scenarios supported by ``run_ui_scenario``.
_SCENARIO_VIEWS: dict[str, str] = {
    "navigate_library": "Library",
    "navigate_quickcopy": "QuickCopy",
    "navigate_updates": "Updates",
    "navigate_settings": "Settings",
}

_FULL_TOUR_SEQUENCE: tuple[str, ...] = (
    "navigate_library",
    "navigate_quickcopy",
    "navigate_updates",
    "navigate_settings",
)


def navigate_view(view: str) -> dict[str, Any]:
    """Navigate the UI to *view*, deterministically, in either MCP mode.

    A headless ``--mcp`` process owns its own offscreen QML window *and* runs
    the ``CommandChannel`` that consumes navigation commands. Sending IPC and
    then blocking on the acknowledgement would therefore deadlock against our
    own consumer, so the view is set in-process. When no QML engine is owned
    here (headless offscreen loading disabled), the live GUI is a separate
    process and its acknowledgement is awaited.
    """
    _log_call("navigate_view")
    if headless_qml_enabled():
        controller = _controller_or_none()
        ui = getattr(controller, "ui", None) if controller is not None else None
        if ui is not None:
            try:
                ui.currentView = view
                return {
                    "ok": True,
                    "view": view,
                    "wait": True,
                    "in_process": True,
                    "verified": str(getattr(ui, "currentView", "")) == view,
                    "error": None,
                }
            except Exception as exc:  # noqa: BLE001
                return {"ok": False, "in_process": True, "error": str(exc)}
    result = send_navigation_command(view, wait=True)
    return result if isinstance(result, dict) else {"ok": bool(result)}


def run_ui_scenario(scenario: str, params: dict | None = None) -> dict[str, Any]:
    """Execute a predefined UI navigation scenario against the live GUI."""
    _log_call("run_ui_scenario")
    try:
        scenario = str(scenario)
        params = params or {}
        if scenario == "full_tour":
            sequence = list(_FULL_TOUR_SEQUENCE)
        elif scenario in _SCENARIO_VIEWS:
            sequence = [scenario]
        else:
            sequence = []

        steps: list[dict[str, Any]] = []
        for index, name in enumerate(sequence, start=1):
            view = _SCENARIO_VIEWS[name]
            try:
                result = navigate_view(view)
                ok = bool(result.get("ok", False))
                steps.append(
                    {
                        "step": index,
                        "action": "navigate",
                        "target": view,
                        "ok": ok,
                        "verified": result.get("verified"),
                        "in_process": bool(result.get("in_process", False)),
                        "error": None if ok else str(result.get("error") or "navigation failed"),
                        "screenshot": None,
                    }
                )
            except Exception as exc:  # noqa: BLE001
                steps.append(
                    {
                        "step": index,
                        "action": "navigate",
                        "target": view,
                        "ok": False,
                        "verified": None,
                        "in_process": False,
                        "error": str(exc),
                        "screenshot": None,
                    }
                )

        result = "passed" if steps and all(step["ok"] for step in steps) else "failed"
        return {
            "ok": True,
            "scenario": scenario,
            "steps": steps,
            "result": result,
            "error": None,
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "scenario": str(scenario),
            "steps": [],
            "result": "failed",
            "error": str(exc),
        }
