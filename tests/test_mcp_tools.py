"""Unit tests for the SkillManager MCP tool handlers.

These tests exercise each tool module's *handler* entry points directly while
monkeypatching the heavy ``skill_manager.mcp.bridge`` functions. They never boot
the Qt application or construct ``AppController`` — the bridge functions are
replaced with lightweight fakes so the suite runs headless and fast.

IMPORTANT: every tool module imports its bridge functions *by name* at module
load time (e.g. ``from skill_manager.mcp.bridge import list_skills``). Patching
``bridge.list_skills`` therefore does NOT affect the handlers — we must patch the
bound name inside each tool module instead.
"""

from __future__ import annotations

from typing import Any

import anyio
import pytest

from skill_manager.mcp.models import ToolResult
from skill_manager.mcp.tools import (
    analyze as analyze_mod,
    build as build_mod,
    debug as debug_mod,
    monitor as monitor_mod,
    write as write_mod,
)


def _run(coro: Any) -> Any:
    """Drive an async analyze handler to completion without an async plugin."""
    return anyio.run(lambda: coro)


# ---------------------------------------------------------------------------
# build.py
# ---------------------------------------------------------------------------
def test_build_lint_returns_structured_result(monkeypatch: pytest.MonkeyPatch) -> None:
    """sm_lint handler returns a ToolResult dict with the bridge's lint output."""
    fake_lint = {"returncode": 0, "passed": True, "stdout": "clean", "stderr": ""}
    monkeypatch.setattr(build_mod, "run_lint", lambda path, fix: fake_lint)

    result = build_mod._HANDLERS["sm_lint"]({"path": "src", "fix": False})

    assert result["ok"] is True
    assert result["tool"] == "sm_lint"
    assert result["data"] == fake_lint
    assert "error" not in result or result["error"] is None


def test_build_lint_passes_fix_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    """sm_lint forwards the fix flag to the bridge."""
    captured: dict[str, Any] = {}

    def _fake_lint(path: str, fix: bool) -> dict[str, Any]:
        captured["path"] = path
        captured["fix"] = fix
        return {"returncode": 0, "passed": True}

    monkeypatch.setattr(build_mod, "run_lint", _fake_lint)

    build_mod._HANDLERS["sm_lint"]({"path": "custom", "fix": True})

    assert captured == {"path": "custom", "fix": True}


def test_build_run_tests_dispatches_async_job(monkeypatch: pytest.MonkeyPatch) -> None:
    """sm_run_tests returns a job_id + running status without awaiting the job."""
    monkeypatch.setattr(build_mod, "run_async_job", lambda fn: "job-123")
    monkeypatch.setattr(build_mod, "run_tests", lambda target, parallel: {"returncode": 0})

    result = build_mod._HANDLERS["sm_run_tests"]({"target": "tests/x.py", "parallel": False})

    assert result["ok"] is True
    assert result["tool"] == "sm_run_tests"
    assert result["data"] == {"job_id": "job-123", "status": "running"}


def test_build_build_dispatches_async_job(monkeypatch: pytest.MonkeyPatch) -> None:
    """sm_build returns a job_id + running status."""
    monkeypatch.setattr(build_mod, "run_async_job", lambda fn: "job-build-9")
    monkeypatch.setattr(build_mod, "run_build", lambda target: {"returncode": 0})

    result = build_mod._HANDLERS["sm_build"]({"target": "win"})

    assert result["ok"] is True
    assert result["data"] == {"job_id": "job-build-9", "status": "running"}


def test_build_job_status_unknown_id(monkeypatch: pytest.MonkeyPatch) -> None:
    """sm_job_status returns ok=False for an unknown job_id."""
    monkeypatch.setattr(build_mod, "get_job", lambda job_id: None)

    result = build_mod._HANDLERS["sm_job_status"]({"job_id": "nope"})

    assert result["ok"] is False
    assert result["tool"] == "sm_job_status"
    assert "unknown job_id" in result["error"]


def test_build_job_status_known_id(monkeypatch: pytest.MonkeyPatch) -> None:
    """sm_job_status returns the job buffer for a known job_id."""
    job = {"job_id": "j1", "status": "done", "result": {"returncode": 0}}
    monkeypatch.setattr(build_mod, "get_job", lambda job_id: job)

    result = build_mod._HANDLERS["sm_job_status"]({"job_id": "j1"})

    assert result["ok"] is True
    assert result["data"] == job


def test_build_tool_schemas_present() -> None:
    """Every build tool is declared in _TOOL_SCHEMAS."""
    assert set(build_mod._TOOL_SCHEMAS) == {
        "sm_lint",
        "sm_run_tests",
        "sm_build",
        "sm_job_status",
    }


# ---------------------------------------------------------------------------
# analyze.py
# ---------------------------------------------------------------------------
def test_analyze_list_skills_shape(monkeypatch: pytest.MonkeyPatch) -> None:
    """sm_list_skills returns a ToolResult envelope with a skills list."""
    skills = [{"name": "a", "local_path": "/a"}, {"name": "b", "local_path": "/b"}]
    monkeypatch.setattr(analyze_mod, "list_skills", lambda include_commands, project_label: skills)

    content = _run(
        analyze_mod._HANDLERS["sm_list_skills"]({"include_commands": True, "project_label": ""})
    )
    payload = ToolResult.model_validate_json(content[0].text).model_dump()

    assert payload["ok"] is True
    assert payload["tool"] == "sm_list_skills"
    assert payload["data"]["skills"] == skills


def test_analyze_list_sources_shape(monkeypatch: pytest.MonkeyPatch) -> None:
    """sm_list_sources returns a ToolResult envelope with a sources list."""
    sources = ["/src/a", "/src/b"]
    monkeypatch.setattr(analyze_mod, "list_sources", lambda: sources)

    content = _run(analyze_mod._HANDLERS["sm_list_sources"]({}))
    payload = ToolResult.model_validate_json(content[0].text).model_dump()

    assert payload["ok"] is True
    assert payload["data"]["sources"] == sources


def test_analyze_list_projects_shape(monkeypatch: pytest.MonkeyPatch) -> None:
    """sm_list_projects returns a ToolResult envelope with a projects list."""
    projects = ["/proj/x"]
    monkeypatch.setattr(analyze_mod, "list_projects", lambda: projects)

    content = _run(analyze_mod._HANDLERS["sm_list_projects"]({}))
    payload = ToolResult.model_validate_json(content[0].text).model_dump()

    assert payload["ok"] is True
    assert payload["data"]["projects"] == projects


def test_analyze_static_analyze_returns_matches(monkeypatch: pytest.MonkeyPatch) -> None:
    """sm_static_analyze returns matches from the bridge."""
    matches = [{"file": "x.py", "line": 1, "text": "foo"}]
    monkeypatch.setattr(analyze_mod, "static_analyze", lambda pattern, path: matches)

    content = _run(analyze_mod._HANDLERS["sm_static_analyze"]({"pattern": "foo", "path": "src"}))
    payload = ToolResult.model_validate_json(content[0].text).model_dump()

    assert payload["ok"] is True
    assert payload["data"]["matches"] == matches


def test_analyze_static_analyze_requires_pattern(monkeypatch: pytest.MonkeyPatch) -> None:
    """sm_static_analyze returns ok=False when pattern is empty."""
    monkeypatch.setattr(analyze_mod, "static_analyze", lambda pattern, path: [])

    content = _run(analyze_mod._HANDLERS["sm_static_analyze"]({"pattern": "", "path": "src"}))
    payload = ToolResult.model_validate_json(content[0].text).model_dump()

    assert payload["ok"] is False
    assert "pattern" in payload["error"]


def test_analyze_handler_exception_becomes_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """A bridge exception degrades to a ToolResult error envelope."""
    monkeypatch.setattr(
        analyze_mod,
        "list_skills",
        lambda include_commands, project_label: (_ for _ in ()).throw(RuntimeError("boom")),
    )

    content = _run(analyze_mod._HANDLERS["sm_list_skills"]({}))
    payload = ToolResult.model_validate_json(content[0].text).model_dump()

    assert payload["ok"] is False
    assert "boom" in payload["error"]


def test_analyze_tool_registry_names() -> None:
    """The analyze handler registry exposes the four expected tools."""
    assert set(analyze_mod._HANDLERS) == {
        "sm_list_skills",
        "sm_list_sources",
        "sm_list_projects",
        "sm_static_analyze",
    }


# ---------------------------------------------------------------------------
# monitor.py
# ---------------------------------------------------------------------------
def test_monitor_get_diagnostics_shape(monkeypatch: pytest.MonkeyPatch) -> None:
    """sm_get_diagnostics returns a ToolResult with an events list."""
    events = [{"ts": "t", "level": "info", "msg": "hi"}]
    monkeypatch.setattr(monitor_mod, "_bridge_get_diagnostics", lambda limit: events)

    result = monitor_mod._handle_get_diagnostics(limit=10)

    assert isinstance(result, ToolResult)
    assert result.ok is True
    assert result.tool == "sm_get_diagnostics"
    assert result.data == {"events": events}


def test_monitor_get_health_shape(monkeypatch: pytest.MonkeyPatch) -> None:
    """sm_get_health returns a ToolResult whose data is the health dict."""
    health = {"healthy": True, "qt_loop_alive": True, "controller_present": True}
    monkeypatch.setattr(monitor_mod, "_bridge_get_health", lambda: health)

    result = monitor_mod._handle_get_health()

    assert result.ok is True
    assert result.tool == "sm_get_health"
    assert result.data == health


def test_monitor_tail_events_shape(monkeypatch: pytest.MonkeyPatch) -> None:
    """sm_tail_events returns a ToolResult with tailed events."""
    events = [{"ts": "t", "level": "warn", "msg": "w"}]
    monkeypatch.setattr(monitor_mod, "_bridge_get_diagnostics", lambda limit: events)

    result = monitor_mod._handle_tail_events(limit=5)

    assert result.ok is True
    assert result.tool == "sm_tail_events"
    assert result.data == {"events": events}


def test_monitor_handler_exception_becomes_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """A bridge exception degrades to a ToolResult error envelope."""
    monkeypatch.setattr(
        monitor_mod,
        "_bridge_get_health",
        lambda: (_ for _ in ()).throw(ValueError("down")),
    )

    result = monitor_mod._handle_get_health()

    assert result.ok is False
    assert result.error is not None
    assert "down" in result.error


def test_monitor_profile_cached_path() -> None:
    """sm_profile (cached/incremental) returns per-stage timings + a bottleneck."""
    handlers = monitor_mod.get_handlers()
    assert "sm_profile" in handlers

    result = handlers["sm_profile"]({})

    assert isinstance(result, ToolResult)
    assert result.ok is True
    assert result.tool == "sm_profile"
    assert result.data is not None
    data: dict[str, Any] = result.data
    assert set(data["stages_ms"]) == {
        "discover_all",
        "entity_conversion",
        "filter_engine",
        "search_engine_build",
        "model_commit",
    }
    assert isinstance(data["bottleneck"], str)
    assert data["bottleneck"] != ""
    assert data["force_full_scan"] is False


def test_monitor_profile_full_scan_path() -> None:
    """sm_profile with force_full_scan=True still returns a valid report."""
    handlers = monitor_mod.get_handlers()

    result = handlers["sm_profile"]({"force_full_scan": True})

    assert result.ok is True
    assert result.tool == "sm_profile"
    assert result.data is not None
    data = result.data
    assert "stages_ms" in data
    assert isinstance(data["bottleneck"], str)
    assert data["bottleneck"] != ""
    assert data["force_full_scan"] is True


def test_monitor_profile_schema_declared() -> None:
    """sm_profile is declared in TOOL_SCHEMAS with the expected input schema."""
    assert "sm_profile" in monitor_mod.TOOL_SCHEMAS
    schema = monitor_mod.TOOL_SCHEMAS["sm_profile"]["inputSchema"]
    assert schema["type"] == "object"
    assert "force_full_scan" in schema["properties"]


# ---------------------------------------------------------------------------
# debug.py
# ---------------------------------------------------------------------------
def test_debug_dump_state_shape(monkeypatch: pytest.MonkeyPatch) -> None:
    """sm_dump_state returns a ToolResult with the state dict."""
    state = {"sources": 2, "projects": 3}
    monkeypatch.setattr(debug_mod, "_bridge_dump_state", lambda: state)

    result = debug_mod._handle_dump_state()

    assert result.ok is True
    assert result.tool == "sm_dump_state"
    assert result.data == state


def test_debug_inspect_controller_shape(monkeypatch: pytest.MonkeyPatch) -> None:
    """sm_inspect_controller returns a ToolResult with the introspection result."""
    info = {"name": "x", "type": "Controller", "methods": ["a"], "signals": ["b"]}
    monkeypatch.setattr(debug_mod, "_bridge_inspect_controller", lambda name: info)

    result = debug_mod._handle_inspect_controller(name="x")

    assert result.ok is True
    assert result.tool == "sm_inspect_controller"
    assert result.data == info


def test_debug_capture_errors_shape(monkeypatch: pytest.MonkeyPatch) -> None:
    """sm_capture_errors returns a ToolResult with an errors list."""
    errors = [{"ts": "t", "level": "error", "msg": "e"}]
    monkeypatch.setattr(debug_mod, "_bridge_capture_errors", lambda limit: errors)

    result = debug_mod._handle_capture_errors(limit=7)

    assert result.ok is True
    assert result.tool == "sm_capture_errors"
    assert result.data == {"errors": errors}


def test_debug_handler_exception_becomes_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """A bridge exception degrades to a ToolResult error envelope."""
    monkeypatch.setattr(
        debug_mod, "_bridge_dump_state", lambda: (_ for _ in ()).throw(RuntimeError("x"))
    )

    result = debug_mod._handle_dump_state()

    assert result.ok is False
    assert result.error is not None
    assert "x" in result.error


# ---------------------------------------------------------------------------
# write.py — gating + AGENTS.md exclusions
# ---------------------------------------------------------------------------
def test_write_gated_when_disabled() -> None:
    """With allow_write=False both write tools refuse with a clear error."""
    handlers = write_mod._bind_handlers(allow_write=False)

    del_result = handlers["sm_delete_skill"]({"skill_id": "my-skill"})
    dep_result = handlers["sm_deploy"]({"skill_id": "my-skill", "target": "x"})

    for result in (del_result, dep_result):
        assert result["ok"] is False
        assert "write mode disabled" in result["error"]


def test_write_delete_skill_allowed(monkeypatch: pytest.MonkeyPatch) -> None:
    """With allow_write=True a non-excluded skill is deleted via the bridge."""
    monkeypatch.setattr(
        write_mod,
        "delete_skill",
        lambda skill_id: {"deleted": True, "skill_id": skill_id, "resolved_path": "/ok/path"},
    )

    handlers = write_mod._bind_handlers(allow_write=True)
    result = handlers["sm_delete_skill"]({"skill_id": "my-skill"})

    assert result["ok"] is True
    assert result["tool"] == "sm_delete_skill"
    assert result["data"]["deleted"] is True


def test_write_delete_skill_excluded_by_skill_id() -> None:
    """A delete targeting an AGENTS.md-excluded path is refused even when allowed."""
    handlers = write_mod._bind_handlers(allow_write=True)
    result = handlers["sm_delete_skill"]({"skill_id": ".agents/skills/secret"})

    assert result["ok"] is False
    assert "refused" in result["error"]


def test_write_delete_skill_excluded_by_resolved_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A delete whose resolved path lands in an excluded dir is refused."""
    monkeypatch.setattr(
        write_mod,
        "delete_skill",
        lambda skill_id: {
            "deleted": True,
            "skill_id": skill_id,
            "resolved_path": "repo/.agents/commands/blocked",
        },
    )

    handlers = write_mod._bind_handlers(allow_write=True)
    result = handlers["sm_delete_skill"]({"skill_id": "anything"})

    assert result["ok"] is False
    assert "excluded directory" in result["error"]


def test_write_delete_skill_bridge_value_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """A ValueError from the bridge becomes a ToolResult error."""
    monkeypatch.setattr(
        write_mod,
        "delete_skill",
        lambda skill_id: (_ for _ in ()).throw(ValueError("missing")),
    )

    handlers = write_mod._bind_handlers(allow_write=True)
    result = handlers["sm_delete_skill"]({"skill_id": "ghost"})

    assert result["ok"] is False
    assert result["error"] is not None
    assert "missing" in result["error"]


def test_write_deploy_allowed_but_not_implemented(monkeypatch: pytest.MonkeyPatch) -> None:
    """sm_deploy is allowed but the bridge raises NotImplementedError -> clear error."""
    monkeypatch.setattr(
        write_mod,
        "deploy",
        lambda skill_id, target: (_ for _ in ()).throw(NotImplementedError()),
    )

    handlers = write_mod._bind_handlers(allow_write=True)
    result = handlers["sm_deploy"]({"skill_id": "s", "target": "t"})

    assert result["ok"] is False
    assert "deploy not yet implemented" in result["error"]


def test_write_deploy_excluded_skill_id() -> None:
    """A deploy targeting an AGENTS.md-excluded path is refused even when allowed."""
    handlers = write_mod._bind_handlers(allow_write=True)
    result = handlers["sm_deploy"]({"skill_id": "TODO.md", "target": "x"})

    assert result["ok"] is False
    assert "refused" in result["error"]


def test_write_is_excluded_helper() -> None:
    """_is_excluded matches the three AGENTS.md markers case/separator-insensitively."""
    assert write_mod._is_excluded(".agents/skills/x")
    assert write_mod._is_excluded(".agents\\commands\\y")
    assert write_mod._is_excluded("TODO.md")
    assert write_mod._is_excluded("SRC/.AGENTS/SKILLS/z")
    assert not write_mod._is_excluded("my-ordinary-skill")


def test_write_tool_schemas_present() -> None:
    """Both write tools are declared in _TOOL_SCHEMAS."""
    assert set(write_mod._TOOL_SCHEMAS) == {"sm_delete_skill", "sm_deploy"}
