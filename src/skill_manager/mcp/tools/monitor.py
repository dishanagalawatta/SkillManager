"""Read-only monitoring MCP tools for the SkillManager MCP server.

This module registers the *observability* MCP tools (``sm_get_diagnostics``,
``sm_get_health``, ``sm_tail_events``). They are pure read-only accessors over
the headless bridge (``skill_manager.mcp.bridge``) and never mutate app state.

Server API pattern
------------------
Registration is written against the standard ``mcp`` Python SDK low-level
``Server`` object (``from mcp.server import Server``). The registration
function decorates ``@server.list_tools()`` and ``@server.call_tool()``
directly, matching the low-level ``Server`` style used by the MCP server
entrypoint. This is consistent with the project's other tool waves; the
sibling ``write.py`` module instead returns schemas/handlers because it needs
to close over an ``allow_write`` gate, but these monitor tools have no such
gate and register directly.

Every tool is safe-wrapped: exceptions are caught and returned as
``ToolResult(ok=False, error=str(e))`` so the MCP server never crashes. Each
call is recorded via ``capture_event("mcp_tool_call", {"tool": ..., "args": ...})``.
"""

from __future__ import annotations

import os
import time
from collections.abc import Callable
from typing import Any

from pydantic import BaseModel, Field

from skill_manager.core.analytics import capture_event
from skill_manager.mcp.bridge import (
    get_diagnostics as _bridge_get_diagnostics,
    get_health as _bridge_get_health,
)
from skill_manager.mcp.models import ToolResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _ok(tool: str, data: dict[str, Any] | None = None) -> ToolResult:
    """Build a successful ToolResult envelope."""
    return ToolResult(ok=True, tool=tool, data=data)


def _err(tool: str, error: str) -> ToolResult:
    """Build a failed ToolResult envelope."""
    return ToolResult(ok=False, tool=tool, error=error)


# ---------------------------------------------------------------------------
# Request models (pydantic v2) — used only for input validation/clarity
# ---------------------------------------------------------------------------
class _GetDiagnosticsArgs(BaseModel):
    limit: int = Field(default=100, ge=1, description="Max number of events.")


class _GetHealthArgs(BaseModel):
    pass


class _TailEventsArgs(BaseModel):
    limit: int = Field(default=50, ge=1, description="Max number of events to tail.")


# ---------------------------------------------------------------------------
# Tool schemas (valid JSON-schema input schemas)
# ---------------------------------------------------------------------------
GET_DIAGNOSTICS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "limit": {
            "type": "integer",
            "default": 100,
            "minimum": 1,
            "description": "Maximum number of diagnostic events to return.",
        }
    },
}

GET_HEALTH_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {},
}

TAIL_EVENTS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "limit": {
            "type": "integer",
            "default": 50,
            "minimum": 1,
            "description": "Maximum number of recent events to tail.",
        }
    },
}

PROFILE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "force_full_scan": {
            "type": "boolean",
            "default": False,
            "description": ("If true, also run a full filesystem scan to measure cold-path cost."),
        }
    },
}


# ---------------------------------------------------------------------------
# Tool handlers
# ---------------------------------------------------------------------------
def _handle_get_diagnostics(limit: int) -> ToolResult:
    """Return recent diagnostic events from the ring buffer."""
    try:
        events = _bridge_get_diagnostics(limit=limit)
    except Exception as exc:  # noqa: BLE001 - surface as ToolResult, never crash
        return _err("sm_get_diagnostics", str(exc))
    return _ok("sm_get_diagnostics", {"events": events})


def _handle_get_health() -> ToolResult:
    """Return a health snapshot of the live app/Qt loop/controller."""
    try:
        health = _bridge_get_health()
    except Exception as exc:  # noqa: BLE001 - surface as ToolResult, never crash
        return _err("sm_get_health", str(exc))
    return _ok("sm_get_health", health)


def _handle_tail_events(limit: int) -> ToolResult:
    """Tail the most recent diagnostic events (newest ``limit``)."""
    try:
        events = _bridge_get_diagnostics(limit=limit)
    except Exception as exc:  # noqa: BLE001 - surface as ToolResult, never crash
        return _err("sm_tail_events", str(exc))
    return _ok("sm_tail_events", {"events": events})


def _handle_profile(force_full_scan: bool) -> ToolResult:
    """Profile the discovery pipeline, returning per-stage timings + bottleneck.

    Runs the real discovery pipeline (``DiscoveryService.discover_all``) and the
    prepared-state heavy stages (entity conversion, FilterEngine, SearchEngine
    build, model commit) WITHOUT a live ``AppController``. Pure read-only: it
    never mutates app state, config, or the on-disk cache beyond what
    ``discover_all`` itself writes for incremental caching (idempotent).

    Analytics is patched to a no-op so the measurement never blocks on network.
    """
    # Keep the Qt import headless and avoid any network telemetry during timing.
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    os.environ.setdefault("SKILL_MANAGER_SKIP_INITIAL_LOAD", "1")
    try:
        import skill_manager.core.analytics as _analytics

        for _n in ("capture_event", "capture_exception", "capture"):
            if hasattr(_analytics, _n):
                setattr(_analytics, _n, lambda *_, **__: None)
    except Exception:  # noqa: BLE001 - analytics patch is best-effort
        pass

    try:
        from skill_manager.core.config import ConfigManager
        from skill_manager.core.discovery import DiscoveryService
        from skill_manager.core.models.entities import (
            FilterState,
            PreparedModelState,
            Skill,
        )
        from skill_manager.core.models.filter_engine import FilterEngine
        from skill_manager.core.models.qt_model import SkillModel
        from skill_manager.core.search import SearchEngine

        cfg = ConfigManager()
        sources = cfg.get("sources", []) or []
        projects = cfg.get("projects", []) or []

        svc = DiscoveryService(sources=sources, projects=projects)

        # Stage 1: discover_all (full scan if requested, else cached/incremental).
        t0 = time.perf_counter()
        result = svc.discover_all(cache_callback=None, force_full_scan=force_full_scan)
        discover_ms = (time.perf_counter() - t0) * 1000.0

        records = result.get("skills", []) or []

        # Stage 2: entity conversion.
        t0 = time.perf_counter()
        all_skills = [Skill.from_dict_fast(rec) for rec in records]
        convert_ms = (time.perf_counter() - t0) * 1000.0

        # Stage 3: FilterEngine + prepare_rows.
        t0 = time.perf_counter()
        engine = FilterEngine()
        fstate = FilterState()
        filtered = engine.filter_skills(all_skills, fstate)
        engine.prepare_rows(filtered)
        filter_ms = (time.perf_counter() - t0) * 1000.0

        # Stage 4: SearchEngine build.
        t0 = time.perf_counter()
        index_skills = [
            {
                "local_path": s.local_path,
                "name": s.name,
                "category": s.category,
                "description": s.description,
                "metadata": {"tags": s.tags},
            }
            for s in all_skills
        ]
        search_engine = SearchEngine(index_skills)
        search_ms = (time.perf_counter() - t0) * 1000.0

        # Stage 5: model commit (replacePreparedState).
        t0 = time.perf_counter()
        categories = sorted({s.category for s in all_skills if s.category})
        prepared = PreparedModelState(
            all_skills=all_skills,
            search_engine=search_engine,
            all_filtered_skills=filtered,
            visible_rows=filtered,
            categories=categories,
            status="profiled",
            generation=1,
        )
        model = SkillModel()
        model.replacePreparedState(prepared)
        commit_ms = (time.perf_counter() - t0) * 1000.0

        stages_ms: dict[str, float] = {
            "discover_all": round(discover_ms, 3),
            "entity_conversion": round(convert_ms, 3),
            "filter_engine": round(filter_ms, 3),
            "search_engine_build": round(search_ms, 3),
            "model_commit": round(commit_ms, 3),
        }

        bottleneck = max(stages_ms, key=lambda k: stages_ms[k])

        return _ok(
            "sm_profile",
            {
                "skill_count": len(records),
                "stages_ms": stages_ms,
                "bottleneck": bottleneck,
                "force_full_scan": force_full_scan,
            },
        )
    except Exception as exc:  # noqa: BLE001 - surface as ToolResult, never crash
        return _err("sm_profile", str(exc))


# ---------------------------------------------------------------------------
# Public dispatch surface
# ---------------------------------------------------------------------------
TOOL_SCHEMAS: dict[str, dict[str, Any]] = {
    "sm_get_diagnostics": {
        "description": (
            "Return the most recent diagnostic events from the SkillManager diagnostic ring buffer."
        ),
        "inputSchema": GET_DIAGNOSTICS_SCHEMA,
    },
    "sm_get_health": {
        "description": (
            "Return a health snapshot: Qt event loop alive, controller "
            "present, diagnostic health, model counts, recent errors."
        ),
        "inputSchema": GET_HEALTH_SCHEMA,
    },
    "sm_tail_events": {
        "description": (
            "Tail the most recent diagnostic events (newest N) from "
            "the SkillManager diagnostic ring buffer."
        ),
        "inputSchema": TAIL_EVENTS_SCHEMA,
    },
    "sm_profile": {
        "description": (
            "Profile the SkillManager discovery pipeline, returning per-stage "
            "timing (discover_all full/cached, entity conversion, FilterEngine, "
            "SearchEngine build, model commit) and the identified bottleneck. "
            "Read-only."
        ),
        "inputSchema": PROFILE_SCHEMA,
    },
}


def get_handlers(_allow_write: bool = False) -> dict[str, Callable[..., Any]]:
    """Return the monitor tool dispatch table (name -> handler).

    Each handler is a thunk that parses its args and emits a ``ToolResult``.
    The ``_allow_write`` parameter is accepted for a uniform module interface
    but is unused: monitor tools are read-only.
    """

    def _dispatch_get_diagnostics(args: dict[str, Any]) -> ToolResult:
        parsed = _GetDiagnosticsArgs(**args)
        capture_event(
            "mcp_tool_call",
            {"tool": "sm_get_diagnostics", "args": {"limit": parsed.limit}},
        )
        return _handle_get_diagnostics(parsed.limit)

    def _dispatch_get_health(_args: dict[str, Any]) -> ToolResult:
        capture_event("mcp_tool_call", {"tool": "sm_get_health", "args": {}})
        return _handle_get_health()

    def _dispatch_tail_events(args: dict[str, Any]) -> ToolResult:
        parsed = _TailEventsArgs(**args)
        capture_event(
            "mcp_tool_call",
            {"tool": "sm_tail_events", "args": {"limit": parsed.limit}},
        )
        return _handle_tail_events(parsed.limit)

    def _dispatch_profile(args: dict[str, Any]) -> ToolResult:
        force_full_scan = bool(args.get("force_full_scan", False))
        capture_event(
            "mcp_tool_call",
            {"tool": "sm_profile", "args": {"force_full_scan": force_full_scan}},
        )
        return _handle_profile(force_full_scan)

    return {
        "sm_get_diagnostics": _dispatch_get_diagnostics,
        "sm_get_health": _dispatch_get_health,
        "sm_tail_events": _dispatch_tail_events,
        "sm_profile": _dispatch_profile,
    }


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------
def register_monitor_tools(_server: Any) -> None:
    """Register the read-only monitoring tools against the MCP ``server``.

    .. deprecated::
        Tool registration now happens centrally in ``server.py`` via a single
        ``list_tools`` / ``call_tool`` pair. This function is retained as a
        no-op so existing importers keep working; it MUST NOT decorate any
        ``call_tool`` handler (the SDK keeps only one such slot).

    The registered tools are:
    * ``sm_get_diagnostics`` — recent diagnostic events (arg ``limit``).
    * ``sm_get_health`` — health snapshot (no args).
    * ``sm_tail_events`` — tail recent events (arg ``limit``).
    """
    return


__all__ = [
    "register_monitor_tools",
    "GET_DIAGNOSTICS_SCHEMA",
    "GET_HEALTH_SCHEMA",
    "TAIL_EVENTS_SCHEMA",
    "PROFILE_SCHEMA",
    "TOOL_SCHEMAS",
    "get_handlers",
]
