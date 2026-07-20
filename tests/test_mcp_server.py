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


def test_register_all_tools_on_fresh_server() -> None:
    """Every register_*_tools function decorates a fresh Server without raising."""
    server = Server("test")

    from skill_manager.mcp.tools.analyze import register_analyze_tools
    from skill_manager.mcp.tools.build import register_build_tools
    from skill_manager.mcp.tools.debug import register_debug_tools
    from skill_manager.mcp.tools.monitor import register_monitor_tools
    from skill_manager.mcp.tools.write import register_write_tools

    register_build_tools(server)
    register_analyze_tools(server)
    register_monitor_tools(server)
    register_debug_tools(server)
    register_write_tools(server, allow_write=False)

    # If we reached here, all five registrations succeeded.
    assert server is not None


def test_register_write_tools_with_allow_write_true() -> None:
    """register_write_tools accepts allow_write=True without raising."""
    server = Server("test-write")

    from skill_manager.mcp.tools.write import register_write_tools

    register_write_tools(server, allow_write=True)

    assert server is not None


def test_expected_tool_names_declared() -> None:
    """Each module exposes its expected tool names in its schema/registry dict."""
    from skill_manager.mcp.tools import analyze, build, write

    assert set(build._TOOL_SCHEMAS) == {
        "sm_lint",
        "sm_run_tests",
        "sm_build",
        "sm_job_status",
    }
    assert set(analyze._HANDLERS) == {
        "sm_list_skills",
        "sm_list_sources",
        "sm_list_projects",
        "sm_static_analyze",
    }
    assert set(write._TOOL_SCHEMAS) == {"sm_delete_skill", "sm_deploy"}


@pytest.mark.parametrize("allow_write", [False, True])
def test_create_mcp_server_parametrized(allow_write: bool) -> None:
    """create_mcp_server constructs cleanly for both gate modes."""
    server = create_mcp_server(allow_write=allow_write)
    assert isinstance(server, Server)
