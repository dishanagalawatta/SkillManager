"""Cached headless ``AppController`` singleton for the MCP bridge."""

from __future__ import annotations

import contextlib
import os
from typing import Any

# ---------------------------------------------------------------------------
# Cached controller singleton
# ---------------------------------------------------------------------------
_APP_CONTROLLER: Any | None = None
_APP_CONTROLLER_ERROR: str | None = None


def _ensure_qapp() -> None:
    """Ensure a QGuiApplication exists; create one headless if needed.

    AppController.__init__ calls ``QGuiApplication.clipboard()``, so a Qt
    application instance must be present before construction. We use the
    offscreen platform to avoid requiring a display.
    """
    from PySide6.QtGui import QGuiApplication

    if QGuiApplication.instance() is not None:
        return

    # Force a headless platform so construction works without a display.
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    # Skip any initial background load triggered by env-driven paths.
    os.environ.setdefault("SKILL_MANAGER_SKIP_INITIAL_LOAD", "1")

    # QApplication is a QGuiApplication subclass and satisfies clipboard().
    from PySide6.QtWidgets import QApplication

    QApplication([])  # type: ignore[arg-type]


def _sync_controller() -> None:
    """Best-effort initial skill sync so model-backed tools see data immediately.

    This runs on the startup path, before any tool call is served, so it
    stays synchronous: the tool handlers use the async variant, which moves
    the scan off the event loop.
    """
    with contextlib.suppress(Exception):
        # function-local import: breaks the _skills <->_controller cycle
        from ._skills import _scan_sources

        controller = _controller_or_none()
        if controller is None:
            return
        raw_skills = _scan_sources(controller)
        if hasattr(controller, "_library_model"):
            controller._library_model.addOrUpdateSkills(raw_skills)


def get_app_controller() -> Any:
    """Return the cached headless ``AppController``, constructing it on first use.

    Returns the controller on success. If construction fails (e.g. missing
    config in a bare environment), the error is cached and re-raised as a
    ``RuntimeError`` carrying the underlying message so callers can degrade
    gracefully.
    """
    global _APP_CONTROLLER, _APP_CONTROLLER_ERROR  # noqa: PLW0603

    if _APP_CONTROLLER is not None:
        return _APP_CONTROLLER
    if _APP_CONTROLLER_ERROR is not None:
        raise RuntimeError(f"AppController previously failed to construct: {_APP_CONTROLLER_ERROR}")

    _ensure_qapp()
    from skill_manager.app import AppController

    try:
        controller = AppController(skip_initial_load=True)
    except Exception as exc:  # noqa: BLE001 - we must not crash the bridge
        _APP_CONTROLLER_ERROR = str(exc)
        raise RuntimeError(f"Failed to construct AppController: {exc}") from exc

    _APP_CONTROLLER = controller
    _sync_controller()
    return _APP_CONTROLLER


def set_app_controller(controller: Any, *, sync: bool = True) -> None:
    """Register *controller* as the bridge's shared controller singleton.

    The MCP stdio launcher builds its own ``AppController`` (the one it hands to
    ``QGuiApplication`` and, later, the headless QML engine) and registers it
    here so every tool reuses that instance instead of lazily constructing a
    second, engine-less controller.

    Args:
        controller: The controller instance to share.
        sync: Run the initial skill sync so model-backed tools see data.

    Raises:
        ValueError: If *controller* is ``None``.
    """
    global _APP_CONTROLLER, _APP_CONTROLLER_ERROR  # noqa: PLW0603

    if controller is None:
        raise ValueError("controller must not be None")

    _APP_CONTROLLER_ERROR = None
    _APP_CONTROLLER = controller
    if sync:
        _sync_controller()


def reset_app_controller() -> None:
    """Drop the cached controller and any cached construction error (teardown/tests)."""
    global _APP_CONTROLLER, _APP_CONTROLLER_ERROR  # noqa: PLW0603

    _APP_CONTROLLER = None
    _APP_CONTROLLER_ERROR = None


def get_qml_engine(controller: Any | None = None) -> Any | None:
    """Return the Qt QML engine attached to *controller* (or the shared one).

    ``AppController`` stores the engine as ``_qml_engine`` (set by
    ``bootstrap._load_qml_engine``). Alternative attribute names are accepted as
    fallbacks so the lookup stays robust across refactors. Returns ``None``
    instead of raising when no engine is present.
    """
    try:
        if controller is None:
            controller = _controller_or_none()
        if controller is None:
            return None
        for name in ("_qml_engine", "qml_engine", "engine"):
            engine = getattr(controller, name, None)
            if engine is not None and hasattr(engine, "rootObjects"):
                return engine
    except Exception:  # noqa: BLE001 - pure lookup, never fatal
        return None
    return None


def _controller_or_none() -> Any | None:
    """Best-effort controller access; returns None instead of raising."""
    try:
        return get_app_controller()
    except Exception:  # noqa: BLE001
        return None
