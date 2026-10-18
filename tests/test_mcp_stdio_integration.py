"""End-to-end stdio integration tests for the SkillManager MCP server.

Unlike the handler-level tests in ``tests/test_mcp_*.py`` (which monkeypatch the
bridge), these tests spawn the **real** server process —::

    python -m skill_manager.__main__ --mcp

— and speak MCP over its stdin/stdout with the official SDK client. That
exercises the whole stack for real: CLI parsing, ``QGuiApplication`` creation,
``AppController`` bootstrapping, anyio stdio transport, tool registry, and the
tool handlers.

Regression coverage: the stdio transport is anyio-based and used to be driven by
PySide6's ``QtAsyncio``, whose ``QAsyncioTask`` does not expose CPython's
``Task._must_cancel``. The event loop raised ``AttributeError`` while delivering
cancellation, so the server never answered a single request and never exited
when stdin closed. ``test_mcp_stdio_serves_read_only_tools`` and
``test_mcp_stdio_exits_cleanly_when_stdin_closes`` exist to catch a relapse.

Only read-only tools are invoked here: the suite must never mutate the
developer's real skill sources.
"""

from __future__ import annotations

import base64
import io
import json
import os
import subprocess
import sys
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

import anyio
import pytest
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.types import InitializeResult
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parents[1]

#: Hard ceiling for a whole stdio session so a regression cannot wedge CI.
SESSION_TIMEOUT_S = 240.0

#: Hard ceiling for spawning a server and letting it exit.
SHUTDOWN_TIMEOUT_S = 60.0

SERVER_PARAMS = StdioServerParameters(
    command=sys.executable,
    args=["-m", "skill_manager.__main__", "--mcp"],
    env={"QT_QPA_PLATFORM": "offscreen", "PYTHONUNBUFFERED": "1"},
    cwd=str(PROJECT_ROOT),
)

# The complete tool surface advertised by ``tools/list``.
EXPECTED_TOOL_NAMES: frozenset[str] = frozenset(
    {
        "sm_accessibility_audit",
        "sm_build",
        "sm_capture_errors",
        "sm_compare_screenshot",
        "sm_create_skill",
        "sm_delete_skill",
        "sm_deploy",
        "sm_detect_qml_errors",
        "sm_dump_state",
        "sm_find_visual_issues",
        "sm_get_current_view",
        "sm_get_diagnostics",
        "sm_get_frame_timing",
        "sm_get_health",
        "sm_get_performance_metrics",
        "sm_get_pixel_color",
        "sm_get_skill",
        "sm_get_window_info",
        "sm_inspect_controller",
        "sm_inspect_qml_tree",
        "sm_job_status",
        "sm_lint",
        "sm_list_projects",
        "sm_list_skills",
        "sm_list_sources",
        "sm_measure_startup_time",
        "sm_mouse_click",
        "sm_mouse_move",
        "sm_navigate",
        "sm_profile",
        "sm_run_tests",
        "sm_run_ui_scenario",
        "sm_screenshot",
        "sm_search_skills",
        "sm_static_analyze",
        "sm_sync_skills",
        "sm_tail_events",
        "sm_toggle_debug_overlay",
        "sm_type_text",
        "sm_update_skill",
    }
)

# (tool, arguments) pairs that are safe to call: read-only and non-mutating.
READ_ONLY_CALLS: tuple[tuple[str, dict[str, Any]], ...] = (
    ("sm_get_health", {}),
    ("sm_get_diagnostics", {"limit": 5}),
    ("sm_tail_events", {"limit": 5}),
    ("sm_dump_state", {}),
    ("sm_get_current_view", {}),
    ("sm_detect_qml_errors", {"limit": 5}),
    ("sm_accessibility_audit", {"max_depth": 3}),
    ("sm_get_performance_metrics", {}),
    ("sm_job_status", {"job_id": "does-not-exist"}),
    ("sm_search_skills", {"query": "skill"}),
)

Interaction = Callable[[ClientSession, InitializeResult], Awaitable[Any]]


def _server_environment() -> dict[str, str]:
    """Environment for a directly spawned server process."""
    return {**os.environ, "QT_QPA_PLATFORM": "offscreen", "PYTHONUNBUFFERED": "1"}


def _run_session(
    interaction: Interaction,
    params: StdioServerParameters = SERVER_PARAMS,
) -> Any:
    """Spawn a server, initialize a session, and run *interaction* against it."""

    async def _main() -> Any:
        async with (
            stdio_client(params) as (read_stream, write_stream),
            ClientSession(read_stream, write_stream) as session,
        ):
            handshake = await session.initialize()
            return await interaction(session, handshake)

    async def _guarded() -> Any:
        with anyio.fail_after(SESSION_TIMEOUT_S):
            return await _main()

    return anyio.run(_guarded)


@pytest.fixture(scope="module")
def isolated_server(tmp_path_factory: pytest.TempPathFactory) -> tuple[StdioServerParameters, Path]:
    """Server params pointing at a throwaway HOME so the real config is untouched.

    The headless QML engine renders the app offscreen; the launcher disables UI
    state persistence, but an isolated home proves it: the config written by the
    MCP process is this test's, never the developer's.
    """
    home = tmp_path_factory.mktemp("mcp_headless_home")
    # conftest points the whole pytest session at its own data dir and we inherit
    # the environment, so the child must be redirected again explicitly.
    data_dir = home / "data"
    env = {
        **os.environ,
        "HOME": str(home),
        "XDG_DATA_HOME": str(home / ".local" / "share"),
        "XDG_CONFIG_HOME": str(home / ".config"),
        "SKILL_MANAGER_DATA_DIR": str(data_dir),
        "QT_QPA_PLATFORM": "offscreen",
        "PYTHONUNBUFFERED": "1",
        # Never reach a live GUI through the repo-relative IPC drop-dir: this
        # test asserts the *headless* capture path, so it must not depend on
        # whether the developer happens to have SkillManager open.
        "SKILL_MANAGER_MCP_NO_IPC": "1",
    }
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "skill_manager.__main__", "--mcp"],
        env=env,
        cwd=str(PROJECT_ROOT),
    )
    return params, data_dir / "config.json"


def _decode_png(b64: str) -> Image.Image:
    """Decode a base64 PNG payload from ``sm_screenshot``."""
    return Image.open(io.BytesIO(base64.b64decode(b64))).convert("RGB")


@pytest.mark.integration
def test_mcp_stdio_headless_ui_tools_work(
    isolated_server: tuple[StdioServerParameters, Path],
) -> None:
    """UI-introspection tools work in a headless ``--mcp`` process.

    No GUI is running: the server lazily loads ``Main.qml`` on the ``offscreen``
    platform plugin, so the QML tree, accessibility audit, screenshots, pixel
    sampling and forced render timings all produce real data.
    """
    params, _config_path = isolated_server

    async def interaction(session: ClientSession, _handshake: InitializeResult) -> dict[str, Any]:
        results: dict[str, Any] = {}
        for tool_name, arguments in (
            ("sm_inspect_qml_tree", {"max_depth": 2}),
            ("sm_accessibility_audit", {"max_depth": 4}),
            ("sm_screenshot", {}),
            ("sm_get_pixel_color", {"x": 5, "y": 5}),
            ("sm_get_frame_timing", {"duration_s": 0.5, "force_render": True}),
            # Health last: it reports the engine status, which only becomes
            # "loaded" once a QML-backed tool has pulled the engine in.
            ("sm_get_health", {}),
        ):
            result = await session.call_tool(tool_name, arguments)
            results[tool_name] = _envelope(result, tool_name)
        return results

    results = _run_session(interaction, params)

    health = results["sm_get_health"]["data"]
    assert health is not None
    assert health["qml"]["enabled"] is True
    assert health["qml"]["loaded"] is True

    tree = results["sm_inspect_qml_tree"]
    assert tree["ok"] is True, tree.get("error")
    assert tree["data"]["root_count"] >= 1
    root = tree["data"]["tree"][0]
    assert root["class_name"]
    # Regression: class_name used to be the Python class, which is "QQuickItem"
    # for every QML item and therefore identifies nothing.
    assert root["class_name"] != "QQuickItem", "tree reported the Python class, not the QML type"
    assert root["accessible_role"] == "Window"
    assert root["accessible_name"]
    assert root["width"] > 0 and root["height"] > 0
    assert root["children"], "QML root has no children — the window did not render"

    audit = results["sm_accessibility_audit"]
    assert audit["ok"] is True, audit.get("error")
    audit_data = audit["data"]
    assert audit_data["element_count"] > 0
    # The audit reads Qt's accessible tree (what assistive technology sees), so
    # every issue names a real control role and no container is ever flagged —
    # the class-name classifier produced 8 bogus DialogButtonBox issues and
    # never reported a genuinely unnamed control.
    assert audit_data["source"] == "accessible-tree"
    assert audit_data["accessible_nodes"] > 0
    for issue in audit_data["issues"]:
        assert issue["role"] in {
            "Button",
            "CheckBox",
            "ComboBox",
            "EditableText",
            "Link",
            "MenuItem",
            "PageTab",
            "RadioButton",
            "Slider",
            "SpinBox",
            "Switch",
            "ToolButton",
        }, issue
        assert issue["path"]
        assert "box" not in issue["class_name"].lower(), issue

    shot = results["sm_screenshot"]
    assert shot["ok"] is True, shot.get("error")
    assert shot["data"]["source"] == "headless-qml"
    image = _decode_png(shot["data"]["image_b64"])
    assert image.size == (shot["data"]["width"], shot["data"]["height"])
    # A never-exposed offscreen window renders a single black colour, so a
    # palette check catches "screenshot works but is blank".
    palette = image.getcolors(maxcolors=4096)
    assert palette is None or len(palette) > 10, "headless screenshot is blank"

    pixel = results["sm_get_pixel_color"]
    assert pixel["ok"] is True, pixel.get("error")
    assert pixel["data"]["color"].startswith("#")
    assert pixel["data"]["source"] == "headless-qml"
    assert (pixel["data"]["width"], pixel["data"]["height"]) == image.size

    timing = results["sm_get_frame_timing"]
    assert timing["ok"] is True, timing.get("error")
    assert timing["data"]["mode"] == "forced_60hz"
    assert timing["data"]["frame_count"] >= 1
    assert timing["data"]["avg_frame_ms"] > 0


@pytest.mark.integration
def test_mcp_stdio_headless_does_not_persist_ui_state(
    isolated_server: tuple[StdioServerParameters, Path],
) -> None:
    """Rendering Main.qml offscreen must never write the user's saved UI state.

    A warm-up session lets the app create/normalise its config; the guarded
    session then loads QML, shows the offscreen window and captures a
    screenshot, which is exactly what used to rewrite ``ui_state``.
    """

    async def noop(session: ClientSession, _handshake: InitializeResult) -> None:
        await session.call_tool("sm_get_current_view", {})

    async def render(session: ClientSession, _handshake: InitializeResult) -> None:
        await session.call_tool("sm_inspect_qml_tree", {"max_depth": 1})
        await session.call_tool("sm_screenshot", {})

    params, config_path = isolated_server
    _run_session(noop, params)
    assert config_path.exists(), "warm-up session did not create a config"
    before = config_path.read_bytes()

    _run_session(render, params)

    assert config_path.read_bytes() == before, (
        "headless MCP run rewrote the user's config:\n"
        f"before={json.loads(before)['ui_state']}\n"
        f"after={json.loads(config_path.read_bytes())['ui_state']}"
    )


def _envelope(result: Any, expected_tool: str) -> dict[str, Any]:
    """Decode a ``CallToolResult`` into the JSON ``ToolResult`` envelope.

    Asserts the envelope contract shared by every SkillManager tool: a single
    text content block holding ``{"ok": ..., "tool": ..., "data"/"error": ...}``.
    """
    assert result.content, f"{expected_tool}: empty content"
    block = result.content[0]
    assert block.type == "text", f"{expected_tool}: expected text content, got {block.type}"
    payload = json.loads(block.text)

    assert isinstance(payload, dict), f"{expected_tool}: envelope is not an object"
    assert set(payload) >= {"ok", "tool"}, f"{expected_tool}: malformed envelope {payload}"
    assert payload["tool"] == expected_tool, f"{expected_tool}: tool field is {payload['tool']!r}"
    assert isinstance(payload["ok"], bool), f"{expected_tool}: ok is not a bool"
    assert "data" in payload or "error" in payload, (
        f"{expected_tool}: envelope carries neither data nor error: {payload}"
    )
    return payload


@pytest.mark.integration
def test_mcp_stdio_initialize_reports_server_info() -> None:
    """The real server completes the MCP handshake over stdio."""

    async def interaction(session: ClientSession, handshake: InitializeResult) -> Any:
        return handshake, session.get_server_capabilities()

    handshake, capabilities = _run_session(interaction)

    assert handshake.serverInfo.name == "SkillManager"
    assert handshake.serverInfo.version, "server advertised no version"
    assert capabilities is not None, "no capabilities captured after initialize"
    assert capabilities.tools is not None, "server does not advertise the tools capability"


@pytest.mark.integration
def test_mcp_stdio_lists_all_tools() -> None:
    """``tools/list`` advertises exactly the expected tools with valid schemas."""

    async def interaction(session: ClientSession, _handshake: InitializeResult) -> Any:
        return await session.list_tools()

    listing = _run_session(interaction)
    names = {tool.name for tool in listing.tools}

    assert names == EXPECTED_TOOL_NAMES, (
        f"missing={sorted(EXPECTED_TOOL_NAMES - names)} "
        f"unexpected={sorted(names - EXPECTED_TOOL_NAMES)}"
    )

    for tool in listing.tools:
        assert tool.description, f"{tool.name}: missing description"
        assert tool.inputSchema, f"{tool.name}: missing inputSchema"
        assert tool.inputSchema.get("type") == "object", f"{tool.name}: schema is not an object"


@pytest.mark.integration
def test_mcp_stdio_serves_read_only_tools() -> None:
    """Read-only tools answer with well-formed envelopes through the transport."""

    async def interaction(
        session: ClientSession, _handshake: InitializeResult
    ) -> dict[str, dict[str, Any]]:
        envelopes: dict[str, dict[str, Any]] = {}
        for tool_name, arguments in READ_ONLY_CALLS:
            result = await session.call_tool(tool_name, arguments)
            envelopes[tool_name] = _envelope(result, tool_name)
        return envelopes

    envelopes = _run_session(interaction)

    for tool_name, _ in READ_ONLY_CALLS:
        envelope = envelopes[tool_name]
        # Degraded-but-graceful is fine (no QML engine / no window in CI); a
        # crash that leaks a traceback as the payload is not.
        message = json.dumps(envelope)
        assert "Traceback (most recent call last)" not in message, (
            f"{tool_name}: handler leaked a traceback: {message}"
        )


@pytest.mark.integration
def test_mcp_stdio_unknown_tool_returns_error_envelope() -> None:
    """An unknown tool name yields ``ok: false`` rather than a crash."""

    async def interaction(session: ClientSession, _handshake: InitializeResult) -> dict[str, Any]:
        result = await session.call_tool("sm_does_not_exist", {})
        return _envelope(result, "sm_does_not_exist")

    envelope = _run_session(interaction)

    assert envelope["ok"] is False
    assert "unknown tool" in envelope["error"].lower()


@pytest.mark.integration
def test_mcp_stdio_write_tool_refused_without_allow_write() -> None:
    """Write tools are inert unless the server is started with ``--mcp-allow-write``."""

    async def interaction(session: ClientSession, _handshake: InitializeResult) -> dict[str, Any]:
        result = await session.call_tool(
            "sm_create_skill",
            {"name": "mcp-integration-should-not-exist", "content": "# nope"},
        )
        return _envelope(result, "sm_create_skill")

    envelope = _run_session(interaction)

    assert envelope["ok"] is False
    assert "write mode disabled" in envelope["error"].lower()


@pytest.mark.integration
def test_mcp_stdio_handles_sequential_requests() -> None:
    """One session serves many requests against a single long-lived process."""

    async def interaction(
        session: ClientSession, _handshake: InitializeResult
    ) -> list[dict[str, Any]]:
        envelopes = []
        for _ in range(3):
            result = await session.call_tool("sm_get_health", {})
            envelopes.append(_envelope(result, "sm_get_health"))
        return envelopes

    envelopes = _run_session(interaction)

    assert len(envelopes) == 3
    for envelope in envelopes:
        assert envelope["data"]["controller_present"] is True


@pytest.mark.integration
def test_mcp_stdio_exits_cleanly_when_stdin_closes() -> None:
    """The server must terminate once its client goes away (no event-loop hang).

    With PySide6's ``QtAsyncio`` the stdio loop kept running after stdin closed,
    so MCP clients could never shut the server down.
    """
    process = subprocess.Popen(
        [sys.executable, "-m", "skill_manager.__main__", "--mcp"],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=str(PROJECT_ROOT),
        env=_server_environment(),
    )
    try:
        _, stderr = process.communicate(timeout=SHUTDOWN_TIMEOUT_S)
    except subprocess.TimeoutExpired:
        process.kill()
        process.communicate()
        pytest.fail(
            f"server did not exit within {SHUTDOWN_TIMEOUT_S}s after stdin closed "
            "(event loop hang regression)"
        )

    assert process.returncode == 0, (
        f"unexpected exit code {process.returncode}; "
        f"stderr tail: {stderr.decode(errors='replace')[-2000:]}"
    )
