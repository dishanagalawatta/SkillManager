"""Integration tests for the SkillManager MCP server construction.

These tests verify that ``create_mcp_server`` builds a wired ``Server`` instance
and that every ``register_*_tools`` function can decorate a fresh ``Server``
without raising. They deliberately do NOT run the stdio loop or boot Qt — the
bridge is never invoked, so the suite stays headless and fast.
"""

from __future__ import annotations

import contextlib
import importlib
from pathlib import Path
from typing import Any

import pytest
from mcp.server import Server

from skill_manager.mcp.server import create_mcp_server

# Every module under ``skill_manager.mcp.tools`` that contributes tools.
TOOL_MODULES: tuple[str, ...] = (
    "accessibility",
    "analyze",
    "bug_detection",
    "build",
    "debug",
    "frame_timing",
    "gui",
    "monitor",
    "performance",
    "screenshot",
    "skills",
    "ui_inspection",
    "write",
)

# Total number of tools across all modules (kept in sync deliberately: a silent
# drop or duplicate in the dispatch table would otherwise go unnoticed).
EXPECTED_TOOL_COUNT = 40


def _tool_modules() -> list[Any]:
    """Import every tool module by name so no module escapes these contracts."""
    return [importlib.import_module(f"skill_manager.mcp.tools.{name}") for name in TOOL_MODULES]


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

    The module list is explicit (``TOOL_MODULES``) so a module added to
    ``server.py`` without being listed here is caught by
    ``test_tool_modules_match_the_server()`` rather than silently skipped.
    """
    for mod in _tool_modules():
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


def test_tool_modules_match_the_server() -> None:
    """The aggregated server wires exactly the modules and tools tested here.

    ``create_mcp_server`` merges every module's schemas with ``dict.update``, so
    a tool name defined in two modules would silently shadow one of them and a
    module missing from this test would go unverified.
    """
    source = importlib.import_module("skill_manager.mcp.server").__file__
    assert source is not None
    server_text = Path(source).read_text(encoding="utf-8")
    for name in TOOL_MODULES:
        assert f"from skill_manager.mcp.tools.{name} import" in server_text, (
            f"tool module {name!r} is not listed in TOOL_MODULES/server wiring"
        )

    owners: dict[str, list[str]] = {}
    for mod in _tool_modules():
        for tool_name in mod.TOOL_SCHEMAS:
            owners.setdefault(tool_name, []).append(mod.__name__)

    duplicates = {tool: mods for tool, mods in owners.items() if len(mods) > 1}
    assert duplicates == {}, f"tool names defined in multiple modules: {duplicates}"
    assert len(owners) == EXPECTED_TOOL_COUNT, (
        f"expected {EXPECTED_TOOL_COUNT} tools, found {len(owners)}: {sorted(set(owners) ^ set())}"
    )


def test_all_tool_schemas_are_well_formed() -> None:
    """Every declared tool schema is a usable MCP tool definition.

    Guards the contract the MCP clients rely on: a non-empty description, an
    object ``inputSchema`` whose ``required`` names only real properties, and
    all four annotation hints present as booleans.
    """
    problems: list[str] = []
    for mod in _tool_modules():
        for name, meta in mod.TOOL_SCHEMAS.items():
            if not name.startswith("sm_"):
                problems.append(f"{mod.__name__}: {name!r} is not sm_-prefixed")
            if not str(meta.get("description", "")).strip():
                problems.append(f"{name}: empty description")

            schema = meta.get("inputSchema")
            if not isinstance(schema, dict) or schema.get("type") != "object":
                problems.append(f"{name}: inputSchema must be an object schema")
                continue

            props = schema.get("properties", {})
            required = schema.get("required", [])
            for key in required:
                if key not in props:
                    problems.append(f"{name}: required {key!r} is not a declared property")
            for key, spec in props.items():
                if "description" not in spec:
                    problems.append(f"{name}.{key}: property schema has no description")
                enum = spec.get("enum")
                default = spec.get("default")
                if enum is not None and default is not None and default not in enum:
                    problems.append(f"{name}.{key}: default {default!r} is outside its enum")

            annotations = meta.get("annotations")
            if not isinstance(annotations, dict):
                problems.append(f"{name}: missing annotations")
                continue
            for hint in ("readOnlyHint", "destructiveHint", "idempotentHint", "openWorldHint"):
                if not isinstance(annotations.get(hint), bool):
                    problems.append(f"{name}: annotation {hint!r} must be a bool")

    assert problems == [], "malformed tool schemas:\n" + "\n".join(problems)


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


# ---------------------------------------------------------------------------
# Stdio transport plumbing
#
# The MCP stdio transport is anyio-based, and anyio's asyncio backend needs
# CPython's ``asyncio.Task`` internals (``Task._must_cancel`` / ``_fut_waiter``)
# while delivering cancellation. PySide6's ``QtAsyncio`` runs ``QAsyncioTask``,
# which does not provide them: the loop raised ``AttributeError`` and the server
# answered nothing. These tests pin the fix — the loop is driven by
# ``anyio.run`` on the main thread, with Qt events pumped from a sibling task.
# ---------------------------------------------------------------------------


def test_run_mcp_server_drives_anyio_not_qtasyncio(monkeypatch: pytest.MonkeyPatch) -> None:
    """``run_mcp_server`` must run the stdio loop through ``anyio.run``."""
    from skill_manager.mcp import server as server_mod

    dispatched: dict[str, object] = {}

    def fake_anyio_run(func: object, *args: object, **kwargs: object) -> None:
        dispatched["func"] = func
        dispatched["args"] = args

    monkeypatch.setattr(server_mod.anyio, "run", fake_anyio_run)

    def forbidden_qtasyncio_run(*args: object, **kwargs: object) -> None:
        raise AssertionError("QtAsyncio must not drive the stdio transport")

    with contextlib.suppress(ImportError):  # pragma: no cover - PySide6 always present here
        from PySide6 import QtAsyncio

        monkeypatch.setattr(QtAsyncio, "run", forbidden_qtasyncio_run)

    server_mod.run_mcp_server(allow_write=False)

    assert dispatched["func"] is server_mod._run_stdio_with_qt_pump
    assert len(dispatched["args"]) == 1, "the wired server must be handed to the loop"


def test_run_stdio_with_qt_pump_finishes_when_transport_ends(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The Qt pump task is cancelled once the stdio transport returns."""
    import anyio

    from skill_manager.mcp import server as server_mod

    @contextlib.asynccontextmanager
    async def fake_stdio_server():  # type: ignore[no-untyped-def]
        yield None, None

    class _StubServer:
        async def run(self, *args: object, **kwargs: object) -> None:
            await anyio.sleep(0)  # return immediately, as if stdin closed

        def create_initialization_options(self) -> None:
            return None

    monkeypatch.setattr(server_mod, "stdio_server", fake_stdio_server)

    async def _drive() -> None:
        with anyio.fail_after(5):
            await server_mod._run_stdio_with_qt_pump(_StubServer())  # type: ignore[arg-type]

    anyio.run(_drive)  # must return, not hang on the cancelled pump task


def test_pump_qt_events_delivers_pending_events() -> None:
    """The pump task really hands control back to the Qt event loop."""
    import anyio
    from PySide6.QtCore import QTimer

    from skill_manager.mcp import server as server_mod

    fired: list[str] = []
    QTimer.singleShot(0, lambda: fired.append("tick"))

    async def _drive() -> None:
        with anyio.move_on_after(2):
            await server_mod._pump_qt_events()

    anyio.run(_drive)

    assert fired == ["tick"], "Qt events were never processed while asyncio owned the thread"


def test_pump_qt_events_survives_without_application(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A missing QCoreApplication must not raise out of the pump task."""
    import anyio
    from PySide6.QtCore import QCoreApplication

    from skill_manager.mcp import server as server_mod

    monkeypatch.setattr(QCoreApplication, "instance", staticmethod(lambda: None))

    async def _drive() -> None:
        with anyio.move_on_after(0.2):
            await server_mod._pump_qt_events()

    anyio.run(_drive)  # no exception == pass
