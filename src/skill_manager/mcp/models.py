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
# sm_get_skill
# ---------------------------------------------------------------------------
class GetSkillRequest(BaseModel):
    """Retrieve full content and metadata of a single skill."""

    skill_id: str = Field(description="Skill name, folder name, or local_path.")


class SkillDetail(BaseModel):
    """Detailed view of a skill including body content and files."""

    name: str
    local_path: str
    category: str = ""
    description: str = ""
    content: str = ""
    project_label: str = ""
    is_package: bool = False
    is_command: bool = False
    is_starred: bool = False
    is_archived: bool = False
    client: str = ""
    risk: str = "Unknown"
    source: str = "Unknown"
    files: list[str] = Field(default_factory=list)


class GetSkillResponse(BaseModel):
    """Single skill detail response."""

    found: bool
    skill: SkillDetail | None = None


# ---------------------------------------------------------------------------
# sm_search_skills
# ---------------------------------------------------------------------------
class SearchSkillsRequest(BaseModel):
    """Search skills by query matching name, category, description, or content."""

    query: str = Field(description="Search term or phrase.")
    category: str = Field(default="", description="Optional category filter.")
    project_label: str = Field(default="", description="Optional project label filter.")
    include_commands: bool = Field(default=True, description="Include command-type skills.")
    limit: int = Field(default=50, ge=1, le=500, description="Max results to return.")


class SearchSkillsResponse(BaseModel):
    """Skill search results."""

    count: int
    skills: list[SkillSummary]


# ---------------------------------------------------------------------------
# sm_create_skill
# ---------------------------------------------------------------------------
class CreateSkillRequest(BaseModel):
    """Create a new skill with SKILL.md content."""

    name: str = Field(description="Name/folder of the skill.")
    content: str = Field(description="SKILL.md content (frontmatter + body).")
    source_path: str = Field(
        default="", description="Target source path or project directory; empty = default source."
    )
    description: str = Field(default="", description="Optional short summary.")
    category: str = Field(default="", description="Optional category.")


class CreateSkillResponse(BaseModel):
    """Skill creation outcome."""

    created: bool
    name: str
    local_path: str
    message: str = ""


# ---------------------------------------------------------------------------
# sm_update_skill
# ---------------------------------------------------------------------------
class UpdateSkillRequest(BaseModel):
    """Update content or metadata of an existing skill."""

    skill_id: str = Field(description="Skill name or local_path to update.")
    content: str = Field(default="", description="Updated SKILL.md content.")
    description: str = Field(default="", description="Updated short summary.")
    category: str = Field(default="", description="Updated category.")


class UpdateSkillResponse(BaseModel):
    """Skill update outcome."""

    updated: bool
    skill_id: str
    local_path: str
    message: str = ""


# ---------------------------------------------------------------------------
# sm_sync_skills
# ---------------------------------------------------------------------------
class SyncSkillsRequest(BaseModel):
    """Re-scan skill directories and refresh the library model."""

    force_full_scan: bool = Field(default=False, description="Force deep re-scan of all paths.")


class SyncSkillsResponse(BaseModel):
    """Sync outcome."""

    synced: bool
    count: int
    message: str = ""


# ---------------------------------------------------------------------------
# sm_deploy
# ---------------------------------------------------------------------------
class DeployRequest(BaseModel):
    """Deploy a skill or package to a target project directory."""

    skill_id: str = Field(default="", description="Skill name or local_path to deploy.")
    target: str = Field(default="", description="Deployment target project label or path.")


class DeployResponse(BaseModel):
    """Deployment outcome."""

    deployed: bool = False
    skill_id: str = ""
    target: str = ""
    details: list[dict[str, Any]] = Field(default_factory=list)
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


# ---------------------------------------------------------------------------
# sm_get_current_view
# ---------------------------------------------------------------------------
class GetCurrentViewRequest(BaseModel):
    """Report the currently active QML view (Library / QuickCopy / Settings / …)."""

    pass


class GetCurrentViewResponse(BaseModel):
    """Current view snapshot."""

    view: str
    ok: bool
    error: str | None = None


# ---------------------------------------------------------------------------
# sm_inspect_qml_tree
# ---------------------------------------------------------------------------
class InspectQmlTreeRequest(BaseModel):
    """Capture a bounded snapshot of the QML object tree."""

    max_depth: int = Field(
        default=5, ge=1, le=20, description="Maximum recursion depth into children."
    )


class QmlNode(BaseModel):
    """A single node in the QML tree snapshot."""

    object_name: str
    class_name: str
    visible: bool
    enabled: bool
    x: int
    y: int
    width: int
    height: int
    children: list[QmlNode] = Field(default_factory=list)


class InspectQmlTreeResponse(BaseModel):
    """QML tree inspection result."""

    ok: bool
    root_count: int
    tree: list[QmlNode]
    error: str | None = None


# ---------------------------------------------------------------------------
# sm_get_pixel_color
# ---------------------------------------------------------------------------
class GetPixelColorRequest(BaseModel):
    """Read the pixel color at a screen coordinate (real GUI only)."""

    x: int = Field(description="X coordinate of the pixel to sample.")
    y: int = Field(description="Y coordinate of the pixel to sample.")


class GetPixelColorResponse(BaseModel):
    """Pixel color sample result."""

    ok: bool
    color: str = Field(description="Hex color in #RRGGBB format.")
    r: int = Field(description="Red channel (0-255).")
    g: int = Field(description="Green channel (0-255).")
    b: int = Field(description="Blue channel (0-255).")
    error: str | None = None


# ---------------------------------------------------------------------------
# sm_get_performance_metrics
# ---------------------------------------------------------------------------
class GetPerformanceMetricsRequest(BaseModel):
    """Snapshot process-level performance metrics (memory, CPU, threads)."""

    pass


class PerformanceMetricsResponse(BaseModel):
    """Performance metrics snapshot."""

    ok: bool
    memory_mb: float = Field(description="Resident memory in megabytes.")
    cpu_percent: float = Field(description="CPU usage percent (0-100).")
    thread_count: int = Field(description="Number of live threads.")
    process_id: int = Field(description="OS process identifier.")
    uptime_seconds: float = Field(description="Process uptime in seconds.")
    error: str | None = None


# ---------------------------------------------------------------------------
# sm_measure_startup_time
# ---------------------------------------------------------------------------
class MeasureStartupTimeRequest(BaseModel):
    """Measure application startup time."""

    pass


class MeasureStartupTimeResponse(BaseModel):
    """Startup timing result."""

    ok: bool
    startup_ms: float = Field(description="Startup duration in milliseconds.")
    timestamp: str = Field(description="ISO-8601 timestamp of the measurement.")
    error: str | None = None


# ---------------------------------------------------------------------------
# sm_detect_qml_errors
# ---------------------------------------------------------------------------
class DetectQmlErrorsRequest(BaseModel):
    """Collect recent QML/JavaScript error messages from the Qt message handler."""

    limit: int = Field(default=50, ge=1, le=500, description="Max number of errors to return.")


class QmlError(BaseModel):
    """A single QML error/log entry."""

    ts: str = Field(description="ISO-8601 timestamp of the error.")
    level: str = Field(description="Severity level (debug, info, warning, critical, fatal).")
    msg: str = Field(description="Error message text.")
    file: str | None = Field(default=None, description="Source file where the error occurred.")
    line: int | None = Field(default=None, description="Source line number, if available.")
    column: int | None = Field(default=None, description="Source column number, if available.")


class DetectQmlErrorsResponse(BaseModel):
    """QML error detection result."""

    ok: bool
    count: int
    errors: list[QmlError]
    error: str | None = None


# ---------------------------------------------------------------------------
# sm_compare_screenshot
# ---------------------------------------------------------------------------
class CompareScreenshotRequest(BaseModel):
    """Compare a baseline screenshot against the current (or supplied) GUI screenshot."""

    baseline_b64: str = Field(description="Base64-encoded PNG of the baseline image.")
    current_b64: str | None = Field(
        default=None,
        description="Base64-encoded PNG of the current image; null = capture live GUI.",
    )
    threshold: float = Field(
        default=0.95, ge=0, le=1, description="Similarity threshold (0-1) for pass/fail."
    )


class CompareScreenshotResponse(BaseModel):
    """Screenshot comparison result."""

    ok: bool
    similarity: float = Field(description="Structural similarity score (0-1).")
    diff_pixels: int = Field(description="Number of differing pixels.")
    total_pixels: int = Field(description="Total pixel count of the images.")
    within_threshold: bool = Field(description="True when similarity >= threshold.")
    issues: list[str] = Field(default_factory=list)
    error: str | None = None


# ---------------------------------------------------------------------------
# sm_find_visual_issues
# ---------------------------------------------------------------------------
class VisualIssueType(StrEnum):
    """Category of a detected visual issue."""

    CLIPPING = "clipping"
    CONTRAST = "contrast"
    OVERLAP = "overlap"
    EMPTY = "empty"
    UNKNOWN = "unknown"


class VisualIssueSeverity(StrEnum):
    """Severity of a detected visual issue."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class VisualIssue(BaseModel):
    """A single detected visual issue."""

    type: str = Field(description="Issue category (clipping, contrast, overlap, empty, unknown).")
    severity: str = Field(description="Severity (low, medium, high).")
    description: str = Field(description="Human-readable description of the issue.")
    location: dict | None = Field(
        default=None, description="Normalized location {x, y, width, height} or null."
    )


class FindVisualIssuesRequest(BaseModel):
    """Scan an image for common visual issues (clipping, contrast, overlap)."""

    image_b64: str = Field(description="Base64-encoded PNG image to inspect.")
    check_clipping: bool = Field(default=True, description="Check for text/UI clipping at edges.")
    check_contrast: bool = Field(default=True, description="Check for insufficient color contrast.")
    check_overlap: bool = Field(default=True, description="Check for overlapping UI elements.")


class FindVisualIssuesResponse(BaseModel):
    """Visual issue detection result."""

    ok: bool
    issue_count: int
    issues: list[VisualIssue]
    error: str | None = None


# ---------------------------------------------------------------------------
# sm_run_ui_scenario
# ---------------------------------------------------------------------------
class UiScenario(StrEnum):
    """Named UI navigation scenarios for automated walkthroughs."""

    NAVIGATE_LIBRARY = "navigate_library"
    NAVIGATE_QUICKCOPY = "navigate_quickcopy"
    NAVIGATE_UPDATES = "navigate_updates"
    NAVIGATE_SETTINGS = "navigate_settings"
    FULL_TOUR = "full_tour"


class ScenarioStep(BaseModel):
    """A single step within a UI scenario walkthrough."""

    step: int = Field(description="1-based step index within the scenario.")
    action: str = Field(description="Action performed (click, navigate, wait, …).")
    target: str = Field(description="QML object or view targeted by the action.")
    ok: bool = Field(description="Whether the step completed successfully.")
    error: str | None = Field(default=None, description="Error message if the step failed.")
    screenshot: str | None = Field(
        default=None, description="Base64 PNG captured after the step, if any."
    )


class RunUiScenarioRequest(BaseModel):
    """Execute a predefined UI navigation scenario against the live GUI."""

    scenario: UiScenario = Field(description="Scenario to run.")
    params: dict | None = Field(default=None, description="Optional scenario-specific parameters.")


class RunUiScenarioResponse(BaseModel):
    """UI scenario execution result."""

    ok: bool
    scenario: str
    steps: list[ScenarioStep]
    result: str = Field(description="Outcome: 'passed' or 'failed'.")
    error: str | None = None


# ---------------------------------------------------------------------------
# sm_compare_screenshot (baseline name support)
# ---------------------------------------------------------------------------
# baseline_name is an optional addition to CompareScreenshotRequest.
# Declared here as a separate model for clarity; the request model above
# already accepts baseline_b64. Clients may supply baseline_name instead of
# (or in addition to) baseline_b64 — the server resolves it under
# .agents/screenshots/<baseline_name>.png.


# ---------------------------------------------------------------------------
# sm_get_frame_timing (QML render performance)
# ---------------------------------------------------------------------------
class FrameSample(BaseModel):
    """A single QML render frame timing sample."""

    frame_index: int = Field(description="0-based frame index within the sample window.")
    duration_ms: float = Field(description="Frame render duration in milliseconds.")
    timestamp: str = Field(description="ISO-8601 timestamp of the sample.")


class GetFrameTimingRequest(BaseModel):
    """Capture QML render frame timings over a sampling window."""

    duration_s: float = Field(
        default=2.0, ge=0.5, le=30.0, description="Sampling window in seconds."
    )


class GetFrameTimingResponse(BaseModel):
    """QML frame-timing measurement result."""

    ok: bool
    duration_s: float
    frame_count: int
    fps: float
    avg_frame_ms: float
    p95_frame_ms: float
    max_frame_ms: float
    dropped_frames: int
    samples: list[FrameSample] = Field(default_factory=list)
    error: str | None = None


# ---------------------------------------------------------------------------
# sm_accessibility_audit (QML accessibility issues)
# ---------------------------------------------------------------------------
class A11yIssue(BaseModel):
    """A single accessibility issue found in the QML tree."""

    object_name: str = Field(description="QML objectName of the offending element.")
    class_name: str = Field(description="QML class name of the element.")
    issue_type: str = Field(
        description="Category: missing_role, missing_name, no_keyboard_focus, "
        "unlabeled_button, unannounced_change, low_contrast_text."
    )
    severity: str = Field(description="Severity: low, medium, high.")
    description: str = Field(description="Human-readable description of the issue.")
    suggestion: str | None = Field(
        default=None, description="Suggested fix (e.g. set Accessible.name)."
    )


class AccessibilityAuditRequest(BaseModel):
    """Audit the QML tree for accessibility issues."""

    max_depth: int = Field(default=10, ge=1, le=30, description="Maximum QML tree depth to audit.")


class AccessibilityAuditResponse(BaseModel):
    """Accessibility audit result."""

    ok: bool
    element_count: int
    issue_count: int
    issues: list[A11yIssue] = Field(default_factory=list)
    error: str | None = None
