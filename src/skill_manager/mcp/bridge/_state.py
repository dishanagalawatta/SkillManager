"""Read-only state accessors: diagnostics, health, and controller introspection."""

from __future__ import annotations

import inspect
from typing import Any

from ._controller import _APP_CONTROLLER_ERROR, _controller_or_none
from ._skills import list_projects, list_sources
from ._telemetry import _log_call, get_diagnostic_logger


def get_diagnostics(limit: int = 100) -> list[dict[str, Any]]:
    """Return the most recent diagnostic ring-buffer events."""
    _log_call("get_diagnostics")
    try:
        events = get_diagnostic_logger().get_recent_events(count=limit)
        return [dict(e) for e in events]
    except Exception:  # noqa: BLE001
        return []


def capture_errors(limit: int = 100) -> list[dict[str, Any]]:
    """Return only error-level diagnostic events."""
    _log_call("capture_errors")
    events = get_diagnostics(limit=limit)
    return [e for e in events if e.get("level") == "ERROR"]


def get_health() -> dict[str, Any]:
    """Return a health snapshot: Qt loop alive, controller present, model counts.

    Never raises — on any failure it returns a degraded health dict.
    """
    _log_call("get_health")
    health: dict[str, Any] = {
        "healthy": False,
        "qt_loop_alive": False,
        "controller_present": False,
        "diagnostic_health": "",
        "model_counts": {},
        "recent_errors": 0,
        "degraded_reason": None,
    }

    try:
        from PySide6.QtGui import QGuiApplication

        health["qt_loop_alive"] = QGuiApplication.instance() is not None
    except Exception as exc:  # noqa: BLE001
        health["degraded_reason"] = f"qt_check_failed: {exc}"
        return health

    controller = _controller_or_none()
    if controller is None:
        health["degraded_reason"] = _APP_CONTROLLER_ERROR or "controller_unavailable"
        return health

    health["controller_present"] = True

    try:
        diag = get_diagnostic_logger()
        health["diagnostic_health"] = diag.get_health_status()
        counts = diag.get_diagnostic_counts()
        health["recent_errors"] = counts.get("errors", 0)
    except Exception:  # noqa: BLE001
        pass

    try:
        model = controller._library_model  # noqa: SLF001
        skills: list[Any] = getattr(model, "_all_skills", []) or []
        health["model_counts"] = {
            "library_skills": len(skills),
            "sources": len(list_sources()),
            "projects": len(list_projects()),
        }
    except Exception:  # noqa: BLE001
        pass

    health["healthy"] = bool(
        health["qt_loop_alive"]
        and health["controller_present"]
        and health["diagnostic_health"] != "red"
    )
    return health


def dump_state() -> dict[str, Any]:
    """Serialize a safe subset of AppController state."""
    _log_call("dump_state")
    controller = _controller_or_none()
    if controller is None:
        return {"available": False, "reason": _APP_CONTROLLER_ERROR or "no_controller"}

    state: dict[str, Any] = {"available": True}
    try:
        state["sources"] = list_sources()
        state["projects"] = list_projects()
        state["project_aliases"] = dict(getattr(controller, "_project_aliases", {}) or {})
        state["client_format"] = getattr(controller, "_client_format", "")
        state["default_client"] = controller._config.get(  # noqa: SLF001
            "default_client", "Last Selected"
        )
        model = controller._library_model  # noqa: SLF001
        skills: list[Any] = getattr(model, "_all_skills", []) or []
        state["model_counts"] = {
            "library_skills": len(skills),
            "stats_up_to_date": getattr(controller, "_stats_up_to_date", 0),
            "stats_outdated": getattr(controller, "_stats_outdated", 0),
            "stats_missing": getattr(controller, "_stats_missing", 0),
        }
        # Config keys (names only — never values, which may include secrets).
        try:
            cfg_data = controller._config.data  # noqa: SLF001
            state["config_keys"] = sorted(cfg_data.keys()) if isinstance(cfg_data, dict) else []
        except Exception:  # noqa: BLE001
            state["config_keys"] = []
    except Exception as exc:  # noqa: BLE001
        state["error"] = str(exc)
    return state


def inspect_controller(name: str) -> dict[str, Any]:
    """Introspect the public surface of a sub-controller (read-only, safe)."""
    _log_call("inspect_controller")
    controller = _controller_or_none()
    if controller is None:
        return {"name": name, "found": False, "reason": "no_controller"}

    target = getattr(controller, name, None)
    if target is None:
        return {"name": name, "found": False, "reason": "attribute_not_found"}

    methods: list[str] = []
    signals: list[str] = []
    for attr in dir(target):
        if attr.startswith("_"):
            continue
        try:
            member = getattr(target, attr)
        except Exception:  # noqa: BLE001
            continue
        if isinstance(member, (staticmethod, classmethod)) or callable(member):
            # Signals in PySide6 are instances of Signal; detect by name pattern
            # or by being a non-callable bound signal. We treat anything with a
            # connect() method that is not a plain function as a signal.
            if hasattr(member, "connect") and not inspect.isfunction(member):
                signals.append(attr)
            else:
                methods.append(attr)
        elif hasattr(member, "connect"):
            signals.append(attr)

    return {
        "name": name,
        "found": True,
        "type": type(target).__name__,
        "methods": sorted(methods),
        "signals": sorted(signals),
    }
