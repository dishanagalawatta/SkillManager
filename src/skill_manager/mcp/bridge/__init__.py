"""Headless bridge between the MCP tool layer and the live SkillManager app.

This module is the ONLY place that touches the PySide6/Qt application object.
It lazily constructs a cached, headless ``AppController`` so that MCP tools can
read application state without a display or a ``QQmlApplicationEngine``.

Design rules (per project constraints):
* Construct ``AppController(skip_initial_load=True)`` — no file watchers,
  schedulers, or background discovery are started, keeping the bridge safe in
  tests and CI.
* Every public wrapper is defensive: it catches exceptions and never lets a
  failure propagate to the caller as an unhandled crash.
* Every call is recorded via ``capture_event("mcp_bridge_call", {"fn": ...})``.
* Destructive operations (delete/deploy) only delegate to APIs that genuinely
  exist; otherwise they raise ``NotImplementedError`` rather than guessing.
"""

from __future__ import annotations

from ._accessibility import audit_accessibility
from ._bug_detection import detect_qml_errors, navigate_view, run_ui_scenario

# Phase 2 decomposition: bridge.py became a package. Submodules hold the
# implementation; this facade re-exports the full public surface so the tool
# modules keep working via ``from skill_manager.mcp.bridge import ...``.
# Names not in ``__all__`` carry an inline "noqa: F401" (intentional
# re-exports for tool modules that import them by name, e.g. tools/skills.py).
from ._capture import capture_app_window, capture_app_window_info
from ._controller import _controller_or_none, get_app_controller, set_app_controller  # noqa: F401
from ._devtools import run_build, run_lint, run_tests
from ._frame_timing import get_frame_timing
from ._input import get_window_info, send_mouse_click, send_mouse_move, send_type_text
from ._ipc import (
    ipc_enabled,
    send_capture_command,
    send_debug_overlay_command,
    send_navigation_command,
)
from ._jobs import get_job, run_async_job
from ._performance import get_performance_metrics, measure_startup_time
from ._qml_headless import (
    capture_headless_window,
    enable_headless_qml,
    ensure_qml_engine,
    get_qml_window,
    qml_engine_status,
    reset_headless_qml,
)
from ._skills import (
    create_skill,  # noqa: F401
    delete_skill,
    deploy,
    get_skill,  # noqa: F401
    list_projects,
    list_skills,
    list_sources,
    search_skills,  # noqa: F401
    sync_skills,  # noqa: F401
    update_skill,  # noqa: F401
)
from ._state import capture_errors, dump_state, get_diagnostics, get_health, inspect_controller
from ._static import static_analyze
from ._ui_inspection import get_current_view, get_pixel_color, inspect_qml_tree
from ._visual_analysis import compare_screenshot, find_visual_issues

__all__ = [
    "get_app_controller",
    "list_skills",
    "list_sources",
    "list_projects",
    "get_diagnostics",
    "capture_errors",
    "get_health",
    "dump_state",
    "inspect_controller",
    "static_analyze",
    "run_async_job",
    "get_job",
    "delete_skill",
    "deploy",
    "run_lint",
    "run_tests",
    "run_build",
    "capture_app_window",
    "capture_app_window_info",
    "set_app_controller",
    "ensure_qml_engine",
    "get_qml_window",
    "capture_headless_window",
    "qml_engine_status",
    "enable_headless_qml",
    "reset_headless_qml",
    "send_navigation_command",
    "ipc_enabled",
    "send_capture_command",
    "send_debug_overlay_command",
    "send_mouse_move",
    "send_mouse_click",
    "send_type_text",
    "get_window_info",
    "get_current_view",
    "inspect_qml_tree",
    "get_pixel_color",
    "get_performance_metrics",
    "measure_startup_time",
    "compare_screenshot",
    "find_visual_issues",
    "detect_qml_errors",
    "run_ui_scenario",
    "navigate_view",
    "audit_accessibility",
    "get_frame_timing",
]
