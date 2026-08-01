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
    with contextlib.suppress(Exception):
        from ._skills import sync_skills  # function-local: breaks _skills<->_controller cycle

        sync_skills()
    return _APP_CONTROLLER


def _controller_or_none() -> Any | None:
    """Best-effort controller access; returns None instead of raising."""
    try:
        return get_app_controller()
    except Exception:  # noqa: BLE001
        return None
