"""MCP tool registration for build/dev-tooling operations.

This module wires the SkillManager MCP server to the headless bridge
for the four dev-tooling tools:

* ``sm_lint``       — run ruff over the source tree (synchronous).
* ``sm_run_tests``  — run pytest, dispatched as an async job (returns a job_id).
* ``sm_build``      — run the application build, dispatched as an async job.
* ``sm_job_status`` — poll the status/result of an async job by job_id.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from skill_manager.mcp.bridge import get_job, run_async_job, run_build, run_lint, run_tests
from skill_manager.mcp.models import ToolResult, err, ok

# ---------------------------------------------------------------------------
# Tool schemas with annotations
# ---------------------------------------------------------------------------
TOOL_SCHEMAS: dict[str, dict[str, Any]] = {
    "sm_lint": {
        "description": "Run the project linter (ruff) over the source tree.",
        "annotations": {
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
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
        "description": "Run the pytest suite (optionally a single file or node id). Long runs are dispatched as an async job; the result carries a job_id.",
        "annotations": {
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
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
        "description": "Build the distributable application package. Dispatched as an async job; the result carries a job_id.",
        "annotations": {
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
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
        "annotations": {
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
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
# Per-tool handlers (return ToolResult)
# ---------------------------------------------------------------------------
def _handle_lint(args: dict[str, Any]) -> ToolResult:
    path: str = args.get("path", "src")
    fix: bool = bool(args.get("fix", False))
    result = run_lint(path=path, fix=fix)
    return ok("sm_lint", result)


def _handle_run_tests(args: dict[str, Any]) -> ToolResult:
    target: str = args.get("target", "")
    parallel: bool = bool(args.get("parallel", True))
    job_id = run_async_job(lambda: run_tests(target=target, parallel=parallel))
    return ok("sm_run_tests", {"job_id": job_id, "status": "running"})


def _handle_build(args: dict[str, Any]) -> ToolResult:
    target: str = args.get("target", "")
    job_id = run_async_job(lambda: run_build(target=target))
    return ok("sm_build", {"job_id": job_id, "status": "running"})


def _handle_job_status(args: dict[str, Any]) -> ToolResult:
    job_id: str = args.get("job_id", "")
    job = get_job(job_id)
    if job is None:
        return err("sm_job_status", f"unknown job_id: {job_id!r}")
    return ok("sm_job_status", job)


# ---------------------------------------------------------------------------
# Dispatch table
# ---------------------------------------------------------------------------
_HANDLERS: dict[str, Callable[[dict[str, Any]], ToolResult]] = {
    "sm_lint": _handle_lint,
    "sm_run_tests": _handle_run_tests,
    "sm_build": _handle_build,
    "sm_job_status": _handle_job_status,
}


def get_handlers(_allow_write: bool = False) -> dict[str, Callable[..., Any]]:
    return dict(_HANDLERS)


__all__ = ["TOOL_SCHEMAS", "get_handlers"]
