"""Pydantic v2 request/response schemas for the SkillManager MCP server tools.

This module is the single source of truth for the wire shapes exchanged
between MCP tool handlers and the bridge layer (``skill_manager.mcp.bridge``).

It contains NO runtime logic — only typed models. Keeping it dependency-free
of PySide6 means it can be imported in any environment (including headless
test runners) without a Qt application instance.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class JobStatus(StrEnum):
    """Lifecycle status of an asynchronously dispatched bridge job."""

    RUNNING = "running"
    DONE = "done"
    ERROR = "error"
    TIMEOUT = "timeout"


# ---------------------------------------------------------------------------
# Common envelopes
# ---------------------------------------------------------------------------
class ToolResult(BaseModel):
    """Uniform return envelope for every MCP tool call."""

    ok: bool
    tool: str
    data: dict[str, Any] | None = None
    error: str | None = None


def ok(tool: str, data: dict[str, Any] | None = None) -> ToolResult:
    """Build a successful ``ToolResult``."""
    return ToolResult(ok=True, tool=tool, data=data)


def err(tool: str, error: str) -> ToolResult:
    """Build a failed ``ToolResult``."""
    return ToolResult(ok=False, tool=tool, error=error)


def tool_annotations(
    *,
    read_only_hint: bool = True,
    destructive_hint: bool = True,
    idempotent_hint: bool = False,
    open_world_hint: bool = True,
) -> dict[str, bool]:
    """Build a standard tool annotations dict for MCP ``Tool`` objects.

    Annotations are hints that help clients understand tool behaviour:
    - ``readOnlyHint``: tool does not modify its environment.
    - ``destructiveHint``: tool may perform destructive updates.
    - ``idempotentHint``: repeated calls with same args have no additional effect.
    - ``openWorldHint``: tool interacts with external entities.
    """
    return {
        "readOnlyHint": read_only_hint,
        "destructiveHint": destructive_hint,
        "idempotentHint": idempotent_hint,
        "openWorldHint": open_world_hint,
    }


class Job(BaseModel):
    """Result buffer for a fire-and-forget async job dispatched via the bridge."""

    job_id: str
    status: JobStatus
    result: dict[str, Any] | None = None
    error: str | None = None


# ---------------------------------------------------------------------------
# sm_lint
# ---------------------------------------------------------------------------
class LintRequest(BaseModel):
    """Run the project linter (ruff) over the source tree."""

    path: str = Field(default="src", description="Target path to lint.")
    fix: bool = Field(default=False, description="Apply auto-fixes where safe.")


class LintResponse(BaseModel):
    """Lint outcome summary."""

    returncode: int
    passed: bool
    stdout: str = ""
    stderr: str = ""


# ---------------------------------------------------------------------------
# sm_run_tests
# ---------------------------------------------------------------------------
class RunTestsRequest(BaseModel):
    """Run the pytest suite (optionally a single file or node id)."""

    target: str = Field(default="", description="Test file or node id; empty = full suite.")
    parallel: bool = Field(default=True, description="Use pytest-xdist auto parallelism.")


class RunTestsResponse(BaseModel):
    """Test run outcome summary."""

    returncode: int
    passed: bool
    collected: int | None = None
    failed: int | None = None
    stdout: str = ""
    stderr: str = ""


# ---------------------------------------------------------------------------
# sm_build
# ---------------------------------------------------------------------------
class BuildRequest(BaseModel):
    """Build the distributable application package."""

    target: str = Field(default="", description="Optional build target / variant.")


class BuildResponse(BaseModel):
    """Build outcome summary."""

    returncode: int
    success: bool
    artifact: str | None = None
    stdout: str = ""
    stderr: str = ""


# ---------------------------------------------------------------------------
# sm_list_skills
# ---------------------------------------------------------------------------
class ListSkillsRequest(BaseModel):
    """Enumerate skills known to the library model."""

    include_commands: bool = Field(
        default=True, description="Include command-type skills in the listing."
    )
    project_label: str = Field(
        default="", description="Restrict to a single project label; empty = all."
    )


class SkillSummary(BaseModel):
    """Minimal, serializable projection of a single Skill entity."""

    name: str
    local_path: str
    category: str = ""
    project_label: str = ""
    is_package: bool = False
    is_command: bool = False
    is_starred: bool = False
    is_archived: bool = False
    client: str = ""
    risk: str = "Unknown"
    source: str = "Unknown"


class ListSkillsResponse(BaseModel):
    """Listing of skills."""

    count: int
    skills: list[SkillSummary]


# ---------------------------------------------------------------------------
# sm_list_sources / sm_list_projects
# ---------------------------------------------------------------------------
class ListSourcesRequest(BaseModel):
    """List configured skill source directories."""

    pass


class ListSourcesResponse(BaseModel):
    """Configured source paths."""

    count: int
    sources: list[str]


class ListProjectsRequest(BaseModel):
    """List configured project directories."""

    pass


class ListProjectsResponse(BaseModel):
    """Configured project paths."""

    count: int
    projects: list[str]


# ---------------------------------------------------------------------------
# sm_static_analyze
# ---------------------------------------------------------------------------
class StaticAnalyzeRequest(BaseModel):
    """Grep the repository for a pattern, respecting .gitignore."""

    pattern: str = Field(description="Regular expression to search for.")
    path: str = Field(default="src", description="Root directory to search within.")


class StaticAnalyzeMatch(BaseModel):
    """A single grep match."""

    file: str
    line: int
    text: str


class StaticAnalyzeResponse(BaseModel):
    """Static analysis (grep) results."""

    pattern: str
    scanned_root: str
    match_count: int
    matches: list[StaticAnalyzeMatch]


# ---------------------------------------------------------------------------
# sm_get_diagnostics
# ---------------------------------------------------------------------------
class GetDiagnosticsRequest(BaseModel):
    """Read recent diagnostic ring-buffer events."""

    limit: int = Field(default=100, ge=1, le=1000, description="Max events to return.")


class DiagnosticEvent(BaseModel):
    """A single diagnostic ring-buffer entry."""

    ts: str = ""
    level: str = ""
    category: str = ""
    msg: str = ""
    ctx: dict[str, Any] | None = None
    data: dict[str, Any] | None = None


class GetDiagnosticsResponse(BaseModel):
    """Recent diagnostic events."""

    count: int
    events: list[DiagnosticEvent]


# ---------------------------------------------------------------------------
# sm_get_health
# ---------------------------------------------------------------------------
class GetHealthRequest(BaseModel):
    """Probe overall application/bridge health."""

    pass


class HealthResponse(BaseModel):
    """Health snapshot."""

    healthy: bool
    qt_loop_alive: bool
    controller_present: bool
    diagnostic_health: str = ""
    model_counts: dict[str, int] = Field(default_factory=dict)
    recent_errors: int = 0
    degraded_reason: str | None = None


# ---------------------------------------------------------------------------
# sm_tail_events
# ---------------------------------------------------------------------------
class TailEventsRequest(BaseModel):
    """Tail the most recent diagnostic events (human-friendly)."""

    limit: int = Field(default=20, ge=1, le=1000, description="Max events to return.")


class TailEventsResponse(BaseModel):
    """Tailed events."""

    count: int
    events: list[dict[str, Any]]


# ---------------------------------------------------------------------------
# sm_dump_state
# ---------------------------------------------------------------------------
class DumpStateRequest(BaseModel):
    """Serialize a safe subset of AppController state."""

    pass


class DumpStateResponse(BaseModel):
    """Serialized safe state subset."""

    state: dict[str, Any]


# ---------------------------------------------------------------------------
# sm_inspect_controller
# ---------------------------------------------------------------------------
class InspectControllerRequest(BaseModel):
    """Introspect the public surface of a sub-controller (read-only)."""

    name: str = Field(description="Attribute name of the sub-controller on AppController.")


class InspectControllerResponse(BaseModel):
    """Introspection result."""

    name: str
    type: str
    methods: list[str]
    signals: list[str]


# ---------------------------------------------------------------------------
# sm_capture_errors
# ---------------------------------------------------------------------------
class CaptureErrorsRequest(BaseModel):
    """Collect error-level diagnostic events."""

    limit: int = Field(default=100, ge=1, le=1000, description="Max errors to return.")


class CaptureErrorsResponse(BaseModel):
    """Error-level diagnostic events."""

    count: int
    errors: list[DiagnosticEvent]


# ---------------------------------------------------------------------------
# sm_delete_skill
# ---------------------------------------------------------------------------
class DeleteSkillRequest(BaseModel):
    """Delete a skill by its identifier (resolved to local_path)."""

    skill_id: str = Field(description="Skill name or local_path to delete.")


class DeleteSkillResponse(BaseModel):
    """Deletion outcome."""

    deleted: bool
    skill_id: str
    resolved_path: str | None = None
    message: str = ""


# ---------------------------------------------------------------------------
# sm_deploy
# ---------------------------------------------------------------------------
class DeployRequest(BaseModel):
    """Deploy a skill/package to a target (NOT YET IMPLEMENTED)."""

    skill_id: str = Field(default="", description="Skill to deploy.")
    target: str = Field(default="", description="Deployment target.")


class DeployResponse(BaseModel):
    """Deployment outcome (placeholder)."""

    deployed: bool = False
    message: str = ""


# ---------------------------------------------------------------------------
# sm_job_status
# ---------------------------------------------------------------------------
class JobStatusRequest(BaseModel):
    """Query the status/result of an async job."""

    job_id: str = Field(description="Job identifier returned by the dispatcher.")


class JobStatusResponse(BaseModel):
    """Async job status/result."""

    job: Job
