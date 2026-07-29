"""Integration tests for the SkillManager MCP server construction.

These tests verify that ``create_mcp_server`` builds a wired ``Server`` instance
and that every ``register_*_tools`` function can decorate a fresh ``Server``
without raising. They deliberately do NOT run the stdio loop or boot Qt — the
bridge is never invoked, so the suite stays headless and fast.
"""

from __future__ import annotations

import pytest
from mcp.server import Server

from skill_manager.mcp.server import create_mcp_server


def test_create_mcp_server_readonly_returns_server() -> None:
    """create_mcp_server(False) returns a Server instance without error."""
    server = create_mcp_server(allow_write=False)

    assert isinstance(server, Server)
    assert server is not None


def test_create_mcp_server_write_returns_server() -> None:
    """create_mcp_server(True) returns a Server instance without error."""
    server = create_mcp_server(allow_write=True)

    assert isinstance(server, Server)
    assert server is not None


def test_every_tool_module_exports_schemas_and_handlers() -> None:
    """Every tool module exposes ``TOOL_SCHEMAS`` and ``get_handlers()``.

    The MCP server refactored from per-function ``register_*_tools()`` to
    a data-driven pattern: each module declares its schemas in a dict and
    exposes a ``get_handlers()`` factory.  ``server.py`` imports these and
    wires them into ``Server.list_tools()`` / ``Server.call_tool()``.
    """
    from skill_manager.mcp.tools import (
        analyze,
        build,
        debug,
        gui,
        monitor,
        screenshot,
        skills,
        write,
    )

    for mod in (analyze, build, debug, gui, monitor, screenshot, skills, write):
        assert hasattr(mod, "TOOL_SCHEMAS"), f"{mod.__name__} missing TOOL_SCHEMAS"
        assert hasattr(mod, "get_handlers"), f"{mod.__name__} missing get_handlers()"
        assert isinstance(mod.TOOL_SCHEMAS, dict), f"{mod.__name__}.TOOL_SCHEMAS must be a dict"
        # get_handlers returns a dict mapping tool names to callables
        handlers = mod.get_handlers()
        assert isinstance(handlers, dict), f"{mod.__name__}.get_handlers() must return a dict"
        assert set(handlers) == set(mod.TOOL_SCHEMAS), (
            f"{mod.__name__}: keys in get_handlers() {set(handlers)} "
            f"don't match TOOL_SCHEMAS {set(mod.TOOL_SCHEMAS)}"
        )


def test_expected_tool_names_declared() -> None:
    """Each module exposes its expected tool names in TOOL_SCHEMAS."""
    from skill_manager.mcp.tools import analyze, build, skills, write

    assert set(build.TOOL_SCHEMAS) == {
        "sm_lint",
        "sm_run_tests",
        "sm_build",
        "sm_job_status",
    }
    assert set(analyze.TOOL_SCHEMAS) == {
        "sm_list_skills",
        "sm_list_sources",
        "sm_list_projects",
        "sm_static_analyze",
    }
    assert set(skills.TOOL_SCHEMAS) == {
        "sm_get_skill",
        "sm_search_skills",
        "sm_sync_skills",
    }
    assert set(write.TOOL_SCHEMAS) == {
        "sm_create_skill",
        "sm_update_skill",
        "sm_delete_skill",
        "sm_deploy",
    }


@pytest.mark.parametrize("allow_write", [False, True])
def test_create_mcp_server_parametrized(allow_write: bool) -> None:
    """create_mcp_server constructs cleanly for both gate modes."""
    server = create_mcp_server(allow_write=allow_write)
    assert isinstance(server, Server)
