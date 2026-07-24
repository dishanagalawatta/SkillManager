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

import base64
import contextlib
import ctypes
import inspect
import io
import json
import os
import re
import subprocess
import sys
import threading
import time
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Any

from skill_manager.core.analytics import capture_event
from skill_manager.core.diagnostics import get_diagnostic_logger

# ---------------------------------------------------------------------------
# Cached controller singleton
# ---------------------------------------------------------------------------
_APP_CONTROLLER: Any | None = None
_APP_CONTROLLER_ERROR: str | None = None

# Async job result buffers keyed by job_id.
_JOBS: dict[str, dict[str, Any]] = {}

# Project root (repo root) — used for subprocess-based tools (lint/test/build)
# and for static analysis. Resolved relative to this file:
#   src/skill_manager/mcp/bridge.py -> repo root is 4 levels up.
_REPO_ROOT = Path(__file__).resolve().parents[4]

# Cross-process IPC for sm_screenshot: the headless bridge cannot see the GUI
# window, so it writes a navigate command the GUI watches and polls an ack.
_MCP_ROOT = Path(__file__).resolve().parents[3] / "data" / "mcp"
MCP_COMMANDS_DIR = _MCP_ROOT / "commands"
MCP_ACKS_DIR = _MCP_ROOT / "acks"

# Live GUI window title prefix (Main.qml: title: "Skill Manager").
_WINDOW_TITLE_PREFIX = "skill manager"


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
    return _APP_CONTROLLER


def _controller_or_none() -> Any | None:
    """Best-effort controller access; returns None instead of raising."""
    try:
        return get_app_controller()
    except Exception:  # noqa: BLE001
        return None


def _log_call(fn: str) -> None:
    """Record a bridge call via analytics (never raises)."""
    with contextlib.suppress(Exception):
        capture_event("mcp_bridge_call", {"fn": fn})


# ---------------------------------------------------------------------------
# Read-only state accessors
# ---------------------------------------------------------------------------
def list_skills(include_commands: bool = True, project_label: str = "") -> list[dict[str, Any]]:
    """Enumerate skills from ``AppController._library_model``.

    The model stores skills in ``_all_skills`` (a list of ``Skill`` dataclasses).
    We read that list read-only and project a safe subset of fields. There is no
    ``id``/``status``/``client_format`` field on ``Skill`` — we expose the real
    attributes (name, local_path, category, is_package, client, etc.).
    """
    _log_call("list_skills")
    controller = _controller_or_none()
    if controller is None:
        return []

    model = controller._library_model  # noqa: SLF001 - intentional bridge access
    skills: list[Any] = getattr(model, "_all_skills", []) or []

    out: list[dict[str, Any]] = []
    for skill in skills:
        if not include_commands and getattr(skill, "is_command", False):
            continue
        if project_label and getattr(skill, "project_label", "") != project_label:
            continue
        out.append(
            {
                "name": getattr(skill, "name", ""),
                "local_path": getattr(skill, "local_path", ""),
                "category": getattr(skill, "category", ""),
                "project_label": getattr(skill, "project_label", ""),
                "is_package": getattr(skill, "is_package", False),
                "is_command": getattr(skill, "is_command", False),
                "is_starred": getattr(skill, "is_starred", False),
                "is_archived": getattr(skill, "is_archived", False),
                "client": getattr(skill, "client", ""),
                "risk": getattr(skill, "risk", "Unknown"),
                "source": getattr(skill, "source", "Unknown"),
            }
        )
    return out


def list_sources() -> list[str]:
    """Return configured skill source directories."""
    _log_call("list_sources")
    controller = _controller_or_none()
    if controller is None:
        return []
    sources: list[str] = getattr(controller, "_sources", []) or []
    return list(sources)


def list_projects() -> list[str]:
    """Return configured project directories."""
    _log_call("list_projects")
    controller = _controller_or_none()
    if controller is None:
        return []
    projects: list[str] = getattr(controller, "_projects", []) or []
    return list(projects)


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


def static_analyze(pattern: str, path: str = "src") -> list[dict[str, Any]]:
    """Safe grep over the repo, respecting ``.gitignore`` via pathspec.

    Returns a list of ``{"file", "line", "text"}`` dicts. Uses ``pathspec`` when
    available (matching the project's gitignore semantics); otherwise falls back
    to skipping ``.git`` and common junk directories.
    """
    _log_call("static_analyze")
    root = _REPO_ROOT / path
    if not root.exists():
        return []

    try:
        compiled = re.compile(pattern)
    except re.error as exc:
        return [{"error": f"invalid_pattern: {exc}"}]

    spec = _load_gitignore(root)

    matches: list[dict[str, Any]] = []
    try:
        for file_path in _walk(root):
            rel = file_path.relative_to(_REPO_ROOT)
            if spec is not None and spec.match_file(str(rel)):
                continue
            try:
                with file_path.open("r", encoding="utf-8", errors="ignore") as fh:
                    for lineno, line in enumerate(fh, start=1):
                        if compiled.search(line):
                            matches.append(
                                {
                                    "file": str(rel).replace(os.sep, "/"),
                                    "line": lineno,
                                    "text": line.rstrip("\n"),
                                }
                            )
            except (OSError, UnicodeDecodeError):
                continue
    except Exception as exc:  # noqa: BLE001
        return [{"error": str(exc)}]

    return matches


def _load_gitignore(root: Path) -> Any | None:  # noqa: ARG001
    """Build a pathspec matcher from the repo .gitignore, if present."""
    gitignore = _REPO_ROOT / ".gitignore"
    if not gitignore.exists():
        return None
    try:
        import pathspec  # type: ignore[import-not-found]

        patterns = [
            line.strip()
            for line in gitignore.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.startswith("#")
        ]
        return pathspec.PathSpec.from_lines("gitwildmatch", patterns)
    except Exception:  # noqa: BLE001 - pathspec may be absent; degrade gracefully
        return None


def _walk(root: Path) -> Any:
    """Yield files under root, skipping .git and obvious junk dirs."""
    skip_dirs = {".git", "__pycache__", ".venv", "venv", "node_modules", "build", "dist"}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in skip_dirs]
        for fname in filenames:
            yield Path(dirpath) / fname


# ---------------------------------------------------------------------------
# Async job dispatch (fire-and-forget via BackgroundTaskRunner)
# ---------------------------------------------------------------------------
def run_async_job(func: Callable[..., Any], *args: Any, **kwargs: Any) -> str:
    """Dispatch ``func`` on a background thread, returning a job_id.

    ``BackgroundTaskRunner.run`` is fire-and-forget (returns None), so we keep
    our own result buffer keyed by ``job_id``. Use :func:`get_job` to poll.
    """
    _log_call("run_async_job")
    job_id = uuid.uuid4().hex
    _JOBS[job_id] = {
        "job_id": job_id,
        "status": "running",
        "result": None,
        "error": None,
    }

    def _wrapper() -> None:
        try:
            result = func(*args, **kwargs)
            _JOBS[job_id]["result"] = result
            _JOBS[job_id]["status"] = "done"
        except Exception as exc:  # noqa: BLE001
            _JOBS[job_id]["error"] = str(exc)
            _JOBS[job_id]["status"] = "error"

    try:
        controller = _controller_or_none()
        if controller is not None and hasattr(controller, "task_runner"):
            controller.task_runner.run(_wrapper)  # type: ignore[arg-type]
        else:
            # Fallback: run in a plain daemon thread if no controller.
            threading.Thread(target=_wrapper, daemon=True).start()
    except Exception as exc:  # noqa: BLE001
        _JOBS[job_id]["error"] = str(exc)
        _JOBS[job_id]["status"] = "error"

    return job_id


def get_job(job_id: str) -> dict[str, Any] | None:
    """Return the job buffer for ``job_id`` (or None if unknown)."""
    _log_call("get_job")
    return _JOBS.get(job_id)


# ---------------------------------------------------------------------------
# Destructive operations — only delegate to real, safe public APIs
# ---------------------------------------------------------------------------
def delete_skill(skill_id: str) -> dict[str, Any]:
    """Delete a skill by name or local_path.

    Resolves ``skill_id`` to a ``local_path`` via the library model, then calls
    the real public ``OpsController.deleteSkill(path)``. Raises ``ValueError``
    if the skill cannot be resolved (we never guess/invent a path).
    """
    _log_call("delete_skill")
    controller = _controller_or_none()
    if controller is None:
        raise RuntimeError("AppController unavailable; cannot delete skill.")

    model = controller._library_model  # noqa: SLF001
    skills: list[Any] = getattr(model, "_all_skills", []) or []

    resolved: str | None = None
    for skill in skills:
        name = getattr(skill, "name", "")
        path = getattr(skill, "local_path", "")
        if skill_id in (name, path) or skill_id == path:
            resolved = path
            break

    if not resolved:
        raise ValueError(
            f"Skill id {skill_id!r} did not resolve to a known local_path; "
            "refusing to guess a deletion target."
        )

    ops = getattr(controller, "ops", None)
    if ops is None or not hasattr(ops, "deleteSkill"):
        raise NotImplementedError("OpsController.deleteSkill is not available in this build.")

    ops.deleteSkill(resolved)  # type: ignore[attr-defined]
    return {
        "deleted": True,
        "skill_id": skill_id,
        "resolved_path": resolved,
        "message": f"Dispatched deletion for {resolved}",
    }


def deploy(skill_id: str, target: str) -> dict[str, Any]:  # noqa: ARG001
    """Deploy a skill/package to a target.

    NOT IMPLEMENTED: there is no deploy API anywhere in the codebase. We raise
    rather than invent a destructive operation.
    """
    _log_call("deploy")
    raise NotImplementedError(
        "deploy() is not supported: no deploy API exists in SkillManager. "
        "Implement an explicit OpsController/UpdateController deploy method "
        "before wiring this tool."
    )


# ---------------------------------------------------------------------------
# Subprocess-based dev tools (lint / test / build)
# ---------------------------------------------------------------------------
def _run_subprocess(cmd: list[str], cwd: Path | None = None) -> dict[str, Any]:
    """Run a command, returning a structured result. Never raises.

    Uses ``CREATE_NO_WINDOW`` on Windows to prevent console windows
    from flashing when subprocesses (uv, ruff, pytest) are launched
    from the MCP server in GUI mode.
    """
    try:
        kwargs: dict[str, Any] = {
            "cwd": str(cwd) if cwd else None,
            "capture_output": True,
            "text": True,
            "timeout": 600,
        }
        if sys.platform == "win32":
            kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
        proc = subprocess.run(cmd, **kwargs)
        return {
            "returncode": proc.returncode,
            "stdout": proc.stdout or "",
            "stderr": proc.stderr or "",
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "returncode": -1,
            "stdout": exc.stdout if isinstance(exc.stdout, str) else "",
            "stderr": f"timeout after {exc.timeout}s",
        }
    except Exception as exc:  # noqa: BLE001
        return {"returncode": -1, "stdout": "", "stderr": str(exc)}


def run_lint(path: str = "src", fix: bool = False) -> dict[str, Any]:
    """Run ``uv run ruff`` over the given path."""
    _log_call("run_lint")
    cmd = ["uv", "run", "ruff", "check"]
    if fix:
        cmd.append("--fix")
    cmd.append(path)
    result = _run_subprocess(cmd, cwd=_REPO_ROOT)
    result["passed"] = result["returncode"] == 0
    return result


def run_tests(target: str = "", parallel: bool = True) -> dict[str, Any]:
    """Run pytest, optionally scoped to a single file/node id."""
    _log_call("run_tests")
    cmd = ["uv", "run", "pytest"]
    if parallel:
        cmd += ["-n", "auto"]
    if target:
        cmd.append(target)
    result = _run_subprocess(cmd, cwd=_REPO_ROOT)
    result["passed"] = result["returncode"] == 0
    return result


def run_build(target: str = "") -> dict[str, Any]:
    """Run the application build."""
    _log_call("run_build")
    cmd = ["uv", "run", "skill-manager-build"]
    if target:
        cmd.append(target)
    result = _run_subprocess(cmd, cwd=_REPO_ROOT)
    result["success"] = result["returncode"] == 0
    return result


# ---------------------------------------------------------------------------
# Cross-process window capture + navigation (sm_screenshot)
# ---------------------------------------------------------------------------
class _BITMAPINFOHEADER(ctypes.Structure):  # noqa: N801 - Win32 struct name
    """Minimal BITMAPINFOHEADER for GetDIBits capture."""

    _fields_ = [
        ("biSize", ctypes.c_uint32),
        ("biWidth", ctypes.c_int32),
        ("biHeight", ctypes.c_int32),
        ("biPlanes", ctypes.c_uint16),
        ("biBitCount", ctypes.c_uint16),
        ("biCompression", ctypes.c_uint32),
        ("biSizeImage", ctypes.c_uint32),
        ("biXPelsPerMeter", ctypes.c_int32),
        ("biYPelsPerMeter", ctypes.c_int32),
        ("biClrUsed", ctypes.c_uint32),
        ("biClrImportant", ctypes.c_uint32),
    ]


def _enum_top_level_windows() -> list[int]:
    hwnds: list[int] = []
    try:
        user32 = ctypes.windll.user32  # type: ignore[attr-defined]
        enum_proc = ctypes.WINFUNCTYPE(  # type: ignore[attr-defined]
            ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p
        )

        def _callback(hwnd: int, _lparam: int) -> bool:
            hwnds.append(hwnd)
            return True

        user32.EnumWindows(enum_proc(_callback), 0)
    except Exception:  # noqa: BLE001 - never crash the bridge
        return []
    return hwnds


def _get_window_title(hwnd: int) -> str:
    try:
        user32 = ctypes.windll.user32  # type: ignore[attr-defined]
        length = user32.GetWindowTextLengthW(hwnd)
        if length <= 0:
            return ""
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buf, length + 1)
        return buf.value or ""
    except Exception:  # noqa: BLE001
        return ""


def _get_window_rect(hwnd: int) -> tuple[int, int, int, int] | None:
    try:
        from skill_manager.utils.win32 import RECT

        rect = RECT()
        user32 = ctypes.windll.user32  # type: ignore[attr-defined]
        if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
            return None
        return (rect.left, rect.top, rect.right, rect.bottom)
    except Exception:  # noqa: BLE001
        return None


def _find_skill_manager_window() -> int | None:
    try:
        for hwnd in _enum_top_level_windows():
            title = _get_window_title(hwnd)
            if title and title.lower().startswith(_WINDOW_TITLE_PREFIX):
                return hwnd
    except Exception:  # noqa: BLE001
        return None
    return None


class _WINDOWPLACEMENT(ctypes.Structure):  # noqa: N801
    """Minimal WINDOWPLACEMENT for GetWindowPlacement."""

    _fields_ = [
        ("length", ctypes.c_uint),
        ("flags", ctypes.c_uint),
        ("showCmd", ctypes.c_uint),
        ("ptMinPosition_x", ctypes.c_long),
        ("ptMinPosition_y", ctypes.c_long),
        ("ptMaxPosition_x", ctypes.c_long),
        ("ptMaxPosition_y", ctypes.c_long),
        ("rcNormalLeft", ctypes.c_long),
        ("rcNormalTop", ctypes.c_long),
        ("rcNormalRight", ctypes.c_long),
        ("rcNormalBottom", ctypes.c_long),
    ]


def _get_window_placement(hwnd: int) -> int | None:
    """Return the current show state (SW_*) of the window, or ``None``."""
    try:
        user32 = ctypes.windll.user32  # type: ignore[attr-defined]
        wp = _WINDOWPLACEMENT()
        wp.length = ctypes.sizeof(wp)
        if user32.GetWindowPlacement(hwnd, ctypes.byref(wp)):
            return wp.showCmd
    except Exception:  # noqa: BLE001
        pass
    return None


def _get_normal_rect(hwnd: int) -> tuple[int, int, int, int] | None:
    """Return the window's restored (normal) position from ``WINDOWPLACEMENT``.

    For a minimised window ``GetWindowRect`` returns ``(-32000, -32000)``
    with a tiny size. Use ``GetWindowPlacement.rcNormalPosition`` instead
    to get the dimensions the window will have when restored.
    Returns ``(left, top, right, bottom)`` or ``None``.
    """
    try:
        user32 = ctypes.windll.user32  # type: ignore[attr-defined]
        wp = _WINDOWPLACEMENT()
        wp.length = ctypes.sizeof(wp)
        if user32.GetWindowPlacement(hwnd, ctypes.byref(wp)):
            return (
                wp.rcNormalLeft,
                wp.rcNormalTop,
                wp.rcNormalRight,
                wp.rcNormalBottom,
            )
    except Exception:  # noqa: BLE001
        pass
    return None


def _is_minimized(hwnd: int) -> bool:
    """Check whether the window is currently minimised."""
    show = _get_window_placement(hwnd)
    return show == 2  # SW_SHOWMINIMIZED


def _show_window_force(hwnd: int) -> None:
    """Temporarily restore a minimised window so capture works.

    Uses ``SW_RESTORE`` to restore the window — the caller should follow
    up with PrintWindow (which captures the window's own content regardless
    of overlapping windows) and then minimise again.
    """
    user32 = ctypes.windll.user32  # type: ignore[attr-defined]
    user32.ShowWindow(hwnd, 9)  # SW_RESTORE


def _capture_window_to_image(
    hwnd: int,
    width: int,
    height: int,
    window_left: int = 0,
    window_top: int = 0,
) -> Any | None:
    """Capture the window identified by *hwnd* into a PIL ``Image``.

    Capture strategy:
    1. If minimised — restore the window, sleep 200ms for Qt to paint, then
       call PrintWindow (own-content, unaffected by overlapping windows).
    2. If visible — call PrintWindow directly.
    3. Always emit WM_PRINT message as a secondary capture attempt.
    4. Desktop DC ``BitBlt`` as the final reliable fallback.
    5. If the window was minimised, re-minimise after capture.

    Returns ``None`` on failure.
    """
    try:
        user32 = ctypes.windll.user32  # type: ignore[attr-defined]
        gdi32 = ctypes.windll.gdi32  # type: ignore[attr-defined]

        hwnd_dc = user32.GetWindowDC(hwnd)
        if not hwnd_dc:
            return None
        mem_dc = gdi32.CreateCompatibleDC(hwnd_dc)
        if not mem_dc:
            user32.ReleaseDC(hwnd, hwnd_dc)
            return None
        bitmap = gdi32.CreateCompatibleBitmap(hwnd_dc, width, height)
        if not bitmap:
            gdi32.DeleteDC(mem_dc)
            user32.ReleaseDC(hwnd, hwnd_dc)
            return None
        gdi32.SelectObject(mem_dc, bitmap)

        was_minimized = _is_minimized(hwnd)
        if was_minimized:
            # Qt skips content rendering when minimised — PrintWindow only
            # captures the title bar. Restore first so Qt paints the full UI,
            # then use PrintWindow (which captures own content regardless of
            # overlapping windows).
            _show_window_force(hwnd)
            ctypes.windll.kernel32.Sleep(200)  # wait for Qt paint cycle
            user32.PrintWindow(hwnd, mem_dc, 0x00000002)  # PW_RENDERFULLCONTENT
            user32.PrintWindow(hwnd, mem_dc, 0)
        else:
            # Window is visible — PrintWindow works directly
            user32.PrintWindow(hwnd, mem_dc, 0x00000002)  # PW_RENDERFULLCONTENT
            user32.PrintWindow(hwnd, mem_dc, 0)

        # WM_PRINT — asks the window to paint itself into our DC
        _prf = 0x00000002 | 0x00000004 | 0x00000010 | 0x00000020  # NONCLIENT|CLIENT|CHILDREN|OWNED
        user32.SendMessageTimeoutW(
            hwnd,
            0x0317,
            mem_dc,
            _prf,
            0,
            2000,
            None,
        )

        # Desktop DC BitBlt — reliable when the window is visible on screen
        desk_dc = user32.GetDC(0)
        if desk_dc:
            gdi32.BitBlt(
                mem_dc,
                0,
                0,
                width,
                height,
                desk_dc,
                window_left,
                window_top,
                0x00CC0020,
            )
            user32.ReleaseDC(0, desk_dc)

        if was_minimized:
            user32.ShowWindow(hwnd, 6)  # SW_MINIMIZE

        # ── Read the bitmap data via GetDIBits ────────────────────────────
        bmi = _BITMAPINFOHEADER()
        bmi.biSize = ctypes.sizeof(_BITMAPINFOHEADER)
        bmi.biWidth = width
        bmi.biHeight = -height  # top-down
        bmi.biPlanes = 1
        bmi.biBitCount = 32
        bmi.biCompression = 0  # BI_RGB

        buf_size = width * height * 4
        buf = ctypes.create_string_buffer(buf_size)
        success = gdi32.GetDIBits(mem_dc, bitmap, 0, height, buf, ctypes.byref(bmi), 0)

        gdi32.DeleteObject(bitmap)
        gdi32.DeleteDC(mem_dc)
        user32.ReleaseDC(hwnd, hwnd_dc)

        if not success:
            return None

        from PIL import Image  # type: ignore[import-not-found]

        # GetDIBits with BI_RGB / 32bpp returns pixels in BGRX byte order
        # (Blue, Green, Red, Reserved) on little-endian Windows. Using
        # "RGBA" would swap R↔B, making blue accent appear orange.
        image = Image.frombytes("BGRA", (width, height), buf.raw)
        return image.convert("RGB")
    except Exception:  # noqa: BLE001
        return None


def _pil_image_to_base64(image: Any) -> str | None:
    try:
        buf = io.BytesIO()
        image.save(buf, format="PNG")
        return base64.b64encode(buf.getvalue()).decode("ascii")
    except Exception:  # noqa: BLE001
        return None


def _resize_window(hwnd: int, new_width: int, new_height: int) -> tuple[int, int, int, int] | None:
    """Resize a window via ``SetWindowPos`` and return the previous rect.

    Returns ``(left, top, width, height)`` of the old geometry, or ``None``
    on failure. The caller should restore the original geometry after capture.
    """
    try:
        old_rect = _get_window_rect(hwnd)
        if old_rect is None:
            return None
        left, top, right, bottom = old_rect
        old_w = right - left
        old_h = bottom - top
        user32 = ctypes.windll.user32  # type: ignore[attr-defined]
        swp_nozorder = 0x0004
        swp_noactivate = 0x0010
        user32.SetWindowPos(
            hwnd,
            0,
            left,
            top,
            new_width,
            new_height,
            swp_nozorder | swp_noactivate,
        )
        # Small settle delay for the UI to repaint
        time.sleep(0.15)
        return (left, top, old_w, old_h)
    except Exception:  # noqa: BLE001
        return None


def _restore_window(hwnd: int, left: int, top: int, width: int, height: int) -> None:
    """Restore a window to its previous position and size."""
    try:
        user32 = ctypes.windll.user32  # type: ignore[attr-defined]
        swp_nozorder = 0x0004
        swp_noactivate = 0x0010
        user32.SetWindowPos(
            hwnd,
            0,
            left,
            top,
            width,
            height,
            swp_nozorder | swp_noactivate,
        )
        time.sleep(0.15)
    except Exception:  # noqa: BLE001
        pass


def capture_app_window(
    resize_width: int | None = None,
    resize_height: int | None = None,
) -> tuple[str | None, int, int]:
    """Capture the live SkillManager GUI window cross-process.

    Primary method: file-based IPC to the live Qt GUI — the
    ``CommandChannel._capture_screenshot`` handler calls
    ``QQuickWindow::grabWindow()`` which renders the scene graph to a PNG
    regardless of window visibility state (works minimised, no colour cast).

    Fallback: Win32 PrintWindow + CreateDIBSection capture. Used when the
    IPC path fails (e.g. GUI not running, command channel unavailable).

    Returns ``(base64_png, width, height)`` or ``(None, 0, 0)`` on failure.

    If ``resize_width`` and ``resize_height`` are provided, the window is
    temporarily resized before capture and restored afterward (Win32 fallback
    only — IPC capture always grabs at the window's current resolution).
    """
    _log_call("capture_app_window")
    # Primary: IPC capture via live Qt GUI CommandChannel.
    # Only attempted when the window is found (live GUI process running).
    hwnd_for_ipc = _find_skill_manager_window()
    if hwnd_for_ipc is not None and resize_width is None and resize_height is None:
        ack = send_capture_command(wait=True, timeout=3.0)
        if ack.get("ok"):
            capture_path: str | None = ack.get("capture_path")
            if capture_path:
                try:
                    from PIL import Image  # type: ignore[import-not-found]

                    img = Image.open(capture_path)
                    b64 = _pil_image_to_base64(img)
                    if b64:
                        return (b64, img.width, img.height)
                except Exception:  # noqa: BLE001 — bad PNG, fall through
                    pass

    # ── Fallback: Win32 PrintWindow + CreateDIBSection ───────────────
    try:
        hwnd = _find_skill_manager_window()
        if hwnd is None:
            return (None, 0, 0)

        restore_rect: tuple[int, int, int, int] | None = None
        if resize_width is not None and resize_height is not None:
            restore_rect = _resize_window(hwnd, resize_width, resize_height)

        try:
            rect = _get_window_rect(hwnd)
            if rect is None:
                return (None, 0, 0)
            left, top, right, bottom = rect
            width = max(1, right - left)
            height = max(1, bottom - top)

            # When minimised, GetWindowRect returns (-32000, -32000) →
            # use the restored (normal) position from GetWindowPlacement.
            if _is_minimized(hwnd):
                normal = _get_normal_rect(hwnd)
                if normal is not None:
                    left, top, right, bottom = normal
                    width = max(1, right - left)
                    height = max(1, bottom - top)

            image = _capture_window_to_image(hwnd, width, height, window_left=left, window_top=top)
            if image is None:
                return (None, 0, 0)
            b64 = _pil_image_to_base64(image)
            if b64 is None:
                return (None, 0, 0)
            return (b64, width, height)
        finally:
            if restore_rect is not None:
                _restore_window(hwnd, *restore_rect)
    except Exception:  # noqa: BLE001
        return (None, 0, 0)


def _wait_for_ack(cmd_id: str, acks_dir: Path, timeout: float) -> dict[str, Any]:
    ack_path = acks_dir / f"{cmd_id}.json"
    deadline = time.time() + timeout
    while time.time() < deadline:
        if ack_path.exists():
            try:
                return json.loads(ack_path.read_text(encoding="utf-8"))
            except Exception:  # noqa: BLE001
                return {"ok": False, "error": "invalid ack payload"}
        time.sleep(0.02)
    return {"ok": False}


def _write_command(commands_dir: Path, action: str, **extra: object) -> str:
    """Write a JSON command file and return its ``cmd_id``.

    The GUI's ``CommandChannel`` picks up the file via QTimer polling
    (every 200ms) and processes it asynchronously.
    """
    cmd_id = uuid.uuid4().hex
    command: dict[str, object] = {"action": action, "id": cmd_id, **extra}
    (commands_dir / f"{cmd_id}.json").write_text(json.dumps(command), encoding="utf-8")
    return cmd_id


def send_navigation_command(
    view: str,
    wait: bool = False,
    timeout: float = 2.0,
) -> dict[str, Any]:
    """Send a navigate command to the live GUI via file-based IPC.

    By default (``wait=False``) this is **fire-and-forget**: the command
    is written and the function returns immediately with ``{"ok": True}``
    and the ``cmd_id``. The GUI processes it asynchronously via its
    ``CommandChannel`` (QTimer + QFileSystemWatcher). This means the MCP
    tool never blocks the user's mouse or keyboard.

    When ``wait=True`` the function polls for the acknowledgement file
    for up to *timeout* seconds — useful for callers that need to confirm
    the navigation happened before proceeding.

    Best-effort: returns ``{"ok": False, "error": ...}`` on any failure.
    """
    _log_call("send_navigation_command")
    try:
        commands_dir = MCP_COMMANDS_DIR
        acks_dir = MCP_ACKS_DIR
        commands_dir.mkdir(parents=True, exist_ok=True)
        acks_dir.mkdir(parents=True, exist_ok=True)

        cmd_id = _write_command(commands_dir, "navigate", view=view)

        if wait:
            ack = _wait_for_ack(cmd_id, acks_dir, timeout)
            ack["cmd_id"] = cmd_id
            return ack

        return {"ok": True, "cmd_id": cmd_id, "wait": False}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)}


def send_capture_command(
    wait: bool = False,
    timeout: float = 5.0,
) -> dict[str, Any]:
    """Send a ``capture_screenshot`` command to the live GUI via file-based IPC.

    The GUI's ``CommandChannel._capture_screenshot`` calls
    ``QQuickWindow::grabWindow()`` (works minimised, no colour cast) and saves
    the result as PNG to ``data/mcp/captures/<cmd_id>.png``.

    By default (``wait=False``) this is fire-and-forget — use ``wait=True`` to
    poll for the acknowledgement which includes the PNG path and capture dimensions.

    Best-effort: returns ``{"ok": False, "error": ...}`` on any failure.
    """
    _log_call("send_capture_command")
    try:
        commands_dir = MCP_COMMANDS_DIR
        acks_dir = MCP_ACKS_DIR
        commands_dir.mkdir(parents=True, exist_ok=True)
        acks_dir.mkdir(parents=True, exist_ok=True)

        cmd_id = _write_command(commands_dir, "capture_screenshot")

        if wait:
            ack = _wait_for_ack(cmd_id, acks_dir, timeout)
            ack["cmd_id"] = cmd_id
            return ack

        return {"ok": True, "cmd_id": cmd_id, "wait": False}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)}


def send_debug_overlay_command(
    enabled: bool,
    wait: bool = False,
    timeout: float = 2.0,
) -> dict[str, Any]:
    """Toggle the QuickCopyView ribbon debug overlay on the live GUI via IPC.

    By default (``wait=False``) this is **fire-and-forget**: writes the
    command and returns immediately. Use ``wait=True`` to poll for
    confirmation (up to *timeout* seconds).

    Returns ``{"ok": False, "error": ...}`` on any failure.
    """
    _log_call("send_debug_overlay_command")
    try:
        commands_dir = MCP_COMMANDS_DIR
        acks_dir = MCP_ACKS_DIR
        commands_dir.mkdir(parents=True, exist_ok=True)
        acks_dir.mkdir(parents=True, exist_ok=True)

        cmd_id = _write_command(commands_dir, "set_debug_overlay", enabled=enabled)

        if wait:
            ack = _wait_for_ack(cmd_id, acks_dir, timeout)
            ack["cmd_id"] = cmd_id
            return ack

        return {"ok": True, "cmd_id": cmd_id, "wait": False}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)}


# ---------------------------------------------------------------------------
# Cross-process GUI interaction (mouse + keyboard via Win32)
# ---------------------------------------------------------------------------
def send_mouse_move(x: int, y: int) -> dict[str, Any]:
    """Move the system cursor to screen coordinates (``x``, ``y``).

    Best-effort: returns ``{"ok": True}`` on success, ``{"ok": False, "error": ...}``
    on failure.
    """
    _log_call("send_mouse_move")
    try:
        result = ctypes.windll.user32.SetCursorPos(x, y)  # type: ignore[attr-defined]
        if not result:
            return {"ok": False, "error": "SetCursorPos returned 0"}
        return {"ok": True}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)}


def send_mouse_click(
    x: int | None = None,
    y: int | None = None,
    button: str = "left",
    double: bool = False,
) -> dict[str, Any]:
    """Move the cursor to (``x``, ``y``) if provided and click.

    ``button`` may be ``"left"``, ``"right"``, or ``"middle"``.
    ``double`` performs a double-click when ``True``.

    Best-effort: returns ``{"ok": True}`` on success, ``{"ok": False, "error": ...}``
    on failure.
    """
    _log_call("send_mouse_click")
    try:
        user32 = ctypes.windll.user32  # type: ignore[attr-defined]

        if x is not None and y is not None and not user32.SetCursorPos(x, y):
            return {"ok": False, "error": "SetCursorPos failed"}

        flags: dict[str, tuple[int, int]] = {
            "left": (0x0002, 0x0004),
            "right": (0x0008, 0x0010),
            "middle": (0x0020, 0x0040),
        }
        down_flag, up_flag = flags.get(button, (0x0002, 0x0004))

        for _ in range(2 if double else 1):
            user32.mouse_event(down_flag, 0, 0, 0, 0)
            user32.mouse_event(up_flag, 0, 0, 0, 0)

        return {"ok": True}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)}


def send_type_text(text: str) -> dict[str, Any]:
    """Type ``text`` into the currently focused window via ``SendInput``.

    Handles Shift-key modulation for uppercase letters and common symbols.
    Non-printable characters and unicode beyond basic Latin are skipped.

    Best-effort: returns ``{"ok": True, "chars": N}`` on success,
    ``{"ok": False, "error": ...}`` on failure.
    """
    _log_call("send_type_text")
    try:
        user32 = ctypes.windll.user32  # type: ignore[attr-defined]

        input_keyboard = 1
        keyeventf_keyup = 0x0002

        class KEYBDINPUT(ctypes.Structure):
            _fields_ = [
                ("wVk", ctypes.c_uint16),
                ("wScan", ctypes.c_uint16),
                ("dwFlags", ctypes.c_uint32),
                ("time", ctypes.c_uint32),
                ("dwExtraInfo", ctypes.c_void_p),
            ]

        class _InputUnion(ctypes.Union):
            _fields_ = [("ki", KEYBDINPUT)]

        class INPUT(ctypes.Structure):
            _fields_ = [
                ("type", ctypes.c_uint32),
                ("union", _InputUnion),
            ]

        _vk: dict[str, int] = {
            **{chr(0x30 + i): 0x30 + i for i in range(10)},
            **{chr(0x41 + i): 0x41 + i for i in range(26)},
            "`": 0xC0,
            "~": 0xC0,
            "-": 0xBD,
            "_": 0xBD,
            "=": 0xBB,
            "+": 0xBB,
            "[": 0xDB,
            "{": 0xDB,
            "]": 0xDD,
            "}": 0xDD,
            "\\": 0xDC,
            "|": 0xDC,
            ";": 0xBA,
            ":": 0xBA,
            "'": 0xDE,
            '"': 0xDE,
            ",": 0xBC,
            "<": 0xBC,
            ".": 0xBE,
            ">": 0xBE,
            "/": 0xBF,
            "?": 0xBF,
            " ": 0x20,
            "\n": 0x0D,
            "\t": 0x09,
        }

        _shift_chars: set[str] = set('ABCDEFGHIJKLMNOPQRSTUVWXYZ~!@#$%^&*()_+{}|:"<>?')

        vk_shift = 0x10

        def _make_input(vk: int, flags: int = 0) -> INPUT:
            ki = KEYBDINPUT(wVk=vk, wScan=0, dwFlags=flags, time=0, dwExtraInfo=0)
            return INPUT(type=input_keyboard, union=_InputUnion(ki=ki))

        def _key_down(vk: int) -> INPUT:
            return _make_input(vk, 0)

        def _key_up(vk: int) -> INPUT:
            return _make_input(vk, keyeventf_keyup)

        sentinel = []
        for ch in text:
            vk = _vk.get(ch)
            if vk is None:
                lower = ch.lower()
                vk = _vk.get(lower)
                if vk is None:
                    continue

            need_shift = ch in _shift_chars
            if need_shift:
                sentinel.append(_key_down(vk_shift))
            sentinel.append(_key_down(vk))
            sentinel.append(_key_up(vk))
            if need_shift:
                sentinel.append(_key_up(vk_shift))

        if not sentinel:
            return {"ok": True, "chars": 0}

        n = len(sentinel)
        inputs_type = INPUT * n
        inputs = inputs_type(*sentinel)

        sent = user32.SendInput(n, inputs, ctypes.sizeof(INPUT))
        return {"ok": True, "chars": sent}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)}


def get_window_info() -> dict[str, Any]:
    """Return the live SkillManager window's geometry and DPI.

    Returns ``{"ok": True, "window": {left, top, right, bottom, width, height}}``
    or ``{"ok": False, "error": ...}`` if the window is not found.
    """
    _log_call("get_window_info")
    try:
        hwnd = _find_skill_manager_window()
        if hwnd is None:
            return {"ok": False, "error": "SkillManager window not found"}

        rect = _get_window_rect(hwnd)
        if rect is None:
            return {"ok": False, "error": "GetWindowRect failed"}

        left, top, right, bottom = rect
        return {
            "ok": True,
            "hwnd": hwnd,
            "left": left,
            "top": top,
            "right": right,
            "bottom": bottom,
            "width": right - left,
            "height": bottom - top,
        }
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)}


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
    "send_navigation_command",
    "send_capture_command",
    "send_debug_overlay_command",
    "send_mouse_move",
    "send_mouse_click",
    "send_type_text",
    "get_window_info",
]
