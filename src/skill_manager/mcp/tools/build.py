"""MCP tool registration for build/dev-tooling operations.

This module wires the SkillManager MCP server to the headless bridge
(``skill_manager.mcp.bridge``) for the three dev-tooling tools:

* ``sm_lint``       — run ruff over the source tree (synchronous).
* ``sm_run_tests``  — run pytest, dispatched as an async job (returns a job_id).
* ``sm_build``      — run the application build, dispatched as an async job.
* ``sm_job_status`` — poll the status/result of an async job by job_id.

The server object is a low-level ``mcp.server.Server`` instance. We register a
single ``list_tools`` handler (declaring all four tools) and a single
``call_tool`` handler that dispatches by tool name. Every handler is wrapped so
that exceptions become a ``ToolResult(ok=False, error=...)`` envelope, and every
call is recorded via ``capture_event``.

Only this file is created; the bridge, models, server, and app are owned by
other agents and must not be modified here.
"""

from __future__ import annotations

import contextlib
from collections.abc import Callable
from typing import Any

from mcp.server import Server

from skill_manager.core.analytics import capture_event
from skill_manager.mcp.bridge import get_job, run_async_job, run_build, run_lint, run_tests
from skill_manager.mcp.models import ToolResult

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
    "sm_lint": {
        "description": "Run the project linter (ruff) over the source tree.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Target path to lint.",
                    "default": "src",
                },
                "fix": {
                    "type": "boolean",
                    "description": "Apply auto-fixes where safe.",
                    "default": False,
                },
            },
        },
    },
    "sm_run_tests": {
        "description": "Run the pytest suite (optionally a single file or node id). "
        "Long runs are dispatched as an async job; the result carries a job_id.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "target": {
                    "type": "string",
                    "description": "Test file or node id; empty = full suite.",
                    "default": "",
                },
                "parallel": {
                    "type": "boolean",
                    "description": "Use pytest-xdist auto parallelism.",
                    "default": True,
                },
            },
        },
    },
    "sm_build": {
        "description": "Build the distributable application package. "
        "Dispatched as an async job; the result carries a job_id.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "target": {
                    "type": "string",
                    "description": "Optional build target / variant.",
                    "default": "",
                },
            },
        },
    },
    "sm_job_status": {
        "description": "Query the status/result of an async job by its job_id.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "job_id": {
                    "type": "string",
                    "description": "Job identifier returned by the dispatcher.",
                },
            },
            "required": ["job_id"],
        },
    },
}


# ---------------------------------------------------------------------------
# Per-tool synchronous handlers (return ToolResult dicts)
# ---------------------------------------------------------------------------


def _handle_lint(args: dict[str, Any]) -> dict[str, Any]:
    """Run ruff over ``args['path']`` (optionally fixing)."""
    path: str = args.get("path", "src")
    fix: bool = bool(args.get("fix", False))
    result = run_lint(path=path, fix=fix)
    return _ok("sm_lint", result)


def _handle_run_tests(args: dict[str, Any]) -> dict[str, Any]:
    """Dispatch pytest as an async job; return the job_id + running status."""
    target: str = args.get("target", "")
    parallel: bool = bool(args.get("parallel", True))
    job_id = run_async_job(lambda: run_tests(target=target, parallel=parallel))
    return _ok("sm_run_tests", {"job_id": job_id, "status": "running"})


def _handle_build(args: dict[str, Any]) -> dict[str, Any]:
    """Dispatch the application build as an async job; return job_id + status."""
    target: str = args.get("target", "")
    job_id = run_async_job(lambda: run_build(target=target))
    return _ok("sm_build", {"job_id": job_id, "status": "running"})


def _handle_job_status(args: dict[str, Any]) -> dict[str, Any]:
    """Poll an async job by job_id; return the job buffer (or not-found)."""
    job_id: str = args.get("job_id", "")
    job = get_job(job_id)
    if job is None:
        return _err("sm_job_status", ValueError(f"unknown job_id: {job_id!r}"))
    return _ok("sm_job_status", job)


# Dispatch table: tool name -> handler.
_HANDLERS: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
    "sm_lint": _handle_lint,
    "sm_run_tests": _handle_run_tests,
    "sm_build": _handle_build,
    "sm_job_status": _handle_job_status,
}

# Public schema surface (name -> {description, inputSchema}) for server.py.
TOOL_SCHEMAS: dict[str, dict[str, Any]] = _TOOL_SCHEMAS


def get_handlers(_allow_write: bool = False) -> dict[str, Callable[..., Any]]:
    """Return the build tool dispatch table (name -> handler).

    The ``_allow_write`` parameter is accepted for a uniform module interface
    but is unused: build tools are read-only and never mutate state.
    """
    return dict(_HANDLERS)


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


def register_build_tools(_server: Server[Any]) -> None:
    """Register the build/dev-tooling MCP tools on ``server``.

    .. deprecated::
        Tool registration now happens centrally in ``server.py`` via a single
        ``list_tools`` / ``call_tool`` pair. This function is retained as a
        no-op so existing importers keep working; it MUST NOT decorate any
        ``call_tool`` handler (the SDK keeps only one such slot).
    """
    return


def _json_text(payload: dict[str, Any]) -> str:
    """Serialize a ToolResult envelope to a stable JSON string."""
    import json

    return json.dumps(payload, ensure_ascii=False, default=str)


class _CaptureEventSuppressed:
    """Context manager that records an ``mcp_tool_call`` event, never raising.

    Kept as a tiny helper so the call site stays readable; the analytics call is
    best-effort and must not affect tool execution.
    """

    def __init__(self, tool: str, args: dict[str, Any]) -> None:
        self._tool = tool
        self._args = args

    def __enter__(self) -> None:
        with contextlib.suppress(Exception):
            capture_event("mcp_tool_call", {"tool": self._tool, "args": self._args})

    def __exit__(self, *_exc: object) -> None:
        return None


def _capture_event_suppressed(tool: str, args: dict[str, Any]) -> _CaptureEventSuppressed:
    """Return a context manager that records an ``mcp_tool_call`` event."""
    return _CaptureEventSuppressed(tool, args)


__all__ = ["register_build_tools"]
