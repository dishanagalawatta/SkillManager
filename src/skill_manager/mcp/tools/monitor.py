"""Read-only monitoring MCP tools for the SkillManager MCP server.

This module registers the *observability* MCP tools (``sm_get_diagnostics``,
``sm_get_health``, ``sm_tail_events``, ``sm_profile``). They are pure read-only
accessors over the headless bridge (``skill_manager.mcp.bridge``) and never
mutate app state.
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
from skill_manager.mcp.models import ToolResult, err, ok


# ---------------------------------------------------------------------------
# Request models (pydantic v2)
# ---------------------------------------------------------------------------
class _GetDiagnosticsArgs(BaseModel):
    limit: int = Field(default=100, ge=1, description="Max number of events.")


class _GetHealthArgs(BaseModel):
    pass


class _TailEventsArgs(BaseModel):
    limit: int = Field(default=50, ge=1, description="Max number of events to tail.")


# ---------------------------------------------------------------------------
# Tool schemas with annotations
# ---------------------------------------------------------------------------
TOOL_SCHEMAS: dict[str, dict[str, Any]] = {
    "sm_get_diagnostics": {
        "description": "Return the most recent diagnostic events from the SkillManager diagnostic ring buffer.",
        "annotations": {
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
        "inputSchema": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "default": 100,
                    "minimum": 1,
                    "description": "Maximum number of diagnostic events to return.",
                }
            },
        },
    },
    "sm_get_health": {
        "description": "Return a health snapshot: Qt event loop alive, controller present, diagnostic health, model counts, recent errors.",
        "annotations": {
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
        "inputSchema": {"type": "object", "properties": {}},
    },
    "sm_tail_events": {
        "description": "Tail the most recent diagnostic events (newest N) from the SkillManager diagnostic ring buffer.",
        "annotations": {
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
        "inputSchema": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "default": 50,
                    "minimum": 1,
                    "description": "Maximum number of recent events to tail.",
                }
            },
        },
    },
    "sm_profile": {
        "description": "Profile the SkillManager discovery pipeline, returning per-stage timing and the identified bottleneck. Read-only.",
        "annotations": {
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
        "inputSchema": {
            "type": "object",
            "properties": {
                "force_full_scan": {
                    "type": "boolean",
                    "default": False,
                    "description": "If true, also run a full filesystem scan to measure cold-path cost.",
                }
            },
        },
    },
}


# ---------------------------------------------------------------------------
# Tool handlers
# ---------------------------------------------------------------------------
def _handle_get_diagnostics(limit: int) -> ToolResult:
    try:
        events = _bridge_get_diagnostics(limit=limit)
    except Exception as exc:
        return err("sm_get_diagnostics", str(exc))
    return ok("sm_get_diagnostics", {"events": events})


def _handle_get_health() -> ToolResult:
    try:
        health = _bridge_get_health()
    except Exception as exc:
        return err("sm_get_health", str(exc))
    return ok("sm_get_health", health)


def _handle_tail_events(limit: int) -> ToolResult:
    try:
        events = _bridge_get_diagnostics(limit=limit)
    except Exception as exc:
        return err("sm_tail_events", str(exc))
    return ok("sm_tail_events", {"events": events})


def _handle_profile(force_full_scan: bool) -> ToolResult:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    os.environ.setdefault("SKILL_MANAGER_SKIP_INITIAL_LOAD", "1")
    try:
        import skill_manager.core.analytics as _analytics

        for _n in ("capture_event", "capture_exception", "capture"):
            if hasattr(_analytics, _n):
                setattr(_analytics, _n, lambda *_, **__: None)
    except Exception:
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

        t0 = time.perf_counter()
        result = svc.discover_all(cache_callback=None, force_full_scan=force_full_scan)
        discover_ms = (time.perf_counter() - t0) * 1000.0

        records = result.get("skills", []) or []

        t0 = time.perf_counter()
        all_skills = [Skill.from_dict_fast(rec) for rec in records]
        convert_ms = (time.perf_counter() - t0) * 1000.0

        t0 = time.perf_counter()
        engine = FilterEngine()
        fstate = FilterState()
        filtered = engine.filter_skills(all_skills, fstate)
        engine.prepare_rows(filtered)
        filter_ms = (time.perf_counter() - t0) * 1000.0

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

        return ok(
            "sm_profile",
            {
                "skill_count": len(records),
                "stages_ms": stages_ms,
                "bottleneck": bottleneck,
                "force_full_scan": force_full_scan,
            },
        )
    except Exception as exc:
        return err("sm_profile", str(exc))


# ---------------------------------------------------------------------------
# Public dispatch surface
# ---------------------------------------------------------------------------
def get_handlers(_allow_write: bool = False) -> dict[str, Callable[..., Any]]:
    def _dispatch_get_diagnostics(args: dict[str, Any]) -> ToolResult:
        parsed = _GetDiagnosticsArgs(**args)
        capture_event(
            "mcp_tool_call", {"tool": "sm_get_diagnostics", "args": {"limit": parsed.limit}}
        )
        return _handle_get_diagnostics(parsed.limit)

    def _dispatch_get_health(_args: dict[str, Any]) -> ToolResult:
        capture_event("mcp_tool_call", {"tool": "sm_get_health", "args": {}})
        return _handle_get_health()

    def _dispatch_tail_events(args: dict[str, Any]) -> ToolResult:
        parsed = _TailEventsArgs(**args)
        capture_event("mcp_tool_call", {"tool": "sm_tail_events", "args": {"limit": parsed.limit}})
        return _handle_tail_events(parsed.limit)

    def _dispatch_profile(args: dict[str, Any]) -> ToolResult:
        force_full_scan = bool(args.get("force_full_scan", False))
        capture_event(
            "mcp_tool_call", {"tool": "sm_profile", "args": {"force_full_scan": force_full_scan}}
        )
        return _handle_profile(force_full_scan)

    return {
        "sm_get_diagnostics": _dispatch_get_diagnostics,
        "sm_get_health": _dispatch_get_health,
        "sm_tail_events": _dispatch_tail_events,
        "sm_profile": _dispatch_profile,
    }


__all__ = ["TOOL_SCHEMAS", "get_handlers"]
