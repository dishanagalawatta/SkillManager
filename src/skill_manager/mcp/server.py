"""MCP server entry point for SkillManager.

Builds a low-level :class:`mcp.server.Server`, wires every tool module, and
runs it over stdio.

The MCP stdio transport is built on :mod:`anyio`. anyio's asyncio backend
reaches into CPython ``asyncio.Task`` internals (``task._must_cancel``,
``task._fut_waiter``) while delivering cancellation, which PySide6's
``QAsyncioTask`` does not provide. Running the transport under
:mod:`PySide6.QtAsyncio` therefore raises ``AttributeError`` inside the loop and
the server never answers a single request. We consequently run the stdio loop
with :func:`anyio.run` on the main thread — the same thread that owns
``QGuiApplication`` — and pump Qt events from inside that loop so controller
timers and signal delivery still progress.

Tool modules (``build``, ``analyze``, ``monitor``, ``debug``, ``write``) own
their own ``list_tools`` / ``call_tool`` registration via decorators on the
passed :class:`Server` instance. This module only constructs the server and
delegates registration to each ``register_*_tools`` function — it does NOT
install its own handlers. Imports are performed lazily inside
:func:`create_mcp_server` so a sibling module that is not finished yet does not
break importing this package.
"""

from __future__ import annotations

import contextlib
import inspect
import json
from typing import Any

import anyio
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import CallToolResult, TextContent, Tool, ToolAnnotations

from skill_manager.core.analytics import capture_event
from skill_manager.mcp.models import ToolResult

# How often the stdio loop hands control back to Qt for event processing.
_QT_PUMP_INTERVAL_S = 0.02


def create_mcp_server(allow_write: bool = False) -> Server[Any]:
    """Construct the SkillManager MCP server with all tools registered.

    Every tool module exposes a ``TOOL_SCHEMAS`` dict and a ``get_handlers()``
    callable. This function aggregates them into a SINGLE ``list_tools`` handler
    and a SINGLE ``call_tool`` handler — the low-level ``mcp.server.Server``
    keeps only one ``call_tool`` slot in ``request_handlers[CallToolRequest]``,
    so multiple decorating modules would otherwise overwrite each other.

    Args:
        allow_write: When ``True``, the ``write`` tool family is permitted to
            perform mutating operations; otherwise it is read-only.

    Returns:
        A fully-wired :class:`Server` instance ready to ``run()`` over stdio.
    """
    server: Server[Any] = Server("SkillManager")

    from skill_manager.mcp.tools.accessibility import (
        TOOL_SCHEMAS as ACCESSIBILITY_SCHEMAS,
        get_handlers as accessibility_handlers,
    )
    from skill_manager.mcp.tools.analyze import (
        TOOL_SCHEMAS as ANALYZE_SCHEMAS,
        get_handlers as analyze_handlers,
    )
    from skill_manager.mcp.tools.bug_detection import (
        TOOL_SCHEMAS as BUG_DETECTION_SCHEMAS,
        get_handlers as bug_detection_handlers,
    )
    from skill_manager.mcp.tools.build import (
        TOOL_SCHEMAS as BUILD_SCHEMAS,
        get_handlers as build_handlers,
    )
    from skill_manager.mcp.tools.debug import (
        TOOL_SCHEMAS as DEBUG_SCHEMAS,
        get_handlers as debug_handlers,
    )
    from skill_manager.mcp.tools.frame_timing import (
        TOOL_SCHEMAS as FRAME_TIMING_SCHEMAS,
        get_handlers as frame_timing_handlers,
    )
    from skill_manager.mcp.tools.gui import (
        TOOL_SCHEMAS as GUI_SCHEMAS,
        get_handlers as gui_handlers,
    )
    from skill_manager.mcp.tools.monitor import (
        TOOL_SCHEMAS as MONITOR_SCHEMAS,
        get_handlers as monitor_handlers,
    )
    from skill_manager.mcp.tools.performance import (
        TOOL_SCHEMAS as PERFORMANCE_SCHEMAS,
        get_handlers as performance_handlers,
    )
    from skill_manager.mcp.tools.screenshot import (
        TOOL_SCHEMAS as SCREENSHOT_SCHEMAS,
        get_handlers as screenshot_handlers,
    )
    from skill_manager.mcp.tools.skills import (
        TOOL_SCHEMAS as SKILLS_SCHEMAS,
        get_handlers as skills_handlers,
    )
    from skill_manager.mcp.tools.ui_inspection import (
        TOOL_SCHEMAS as UI_INSPECTION_SCHEMAS,
        get_handlers as ui_inspection_handlers,
    )
    from skill_manager.mcp.tools.write import (
        TOOL_SCHEMAS as WRITE_SCHEMAS,
        get_handlers as write_handlers,
    )

    # Aggregate schemas and handlers from every module into one dispatch table.
    schemas: dict[str, dict[str, Any]] = {}
    handlers: dict[str, Any] = {}
    for module_schemas, module_handlers in (
        (BUILD_SCHEMAS, build_handlers()),
        (ANALYZE_SCHEMAS, analyze_handlers()),
        (ACCESSIBILITY_SCHEMAS, accessibility_handlers()),
        (SKILLS_SCHEMAS, skills_handlers()),
        (MONITOR_SCHEMAS, monitor_handlers()),
        (DEBUG_SCHEMAS, debug_handlers()),
        (FRAME_TIMING_SCHEMAS, frame_timing_handlers()),
        (SCREENSHOT_SCHEMAS, screenshot_handlers()),
        (GUI_SCHEMAS, gui_handlers()),
        (UI_INSPECTION_SCHEMAS, ui_inspection_handlers()),
        (PERFORMANCE_SCHEMAS, performance_handlers()),
        (BUG_DETECTION_SCHEMAS, bug_detection_handlers()),
        (WRITE_SCHEMAS, write_handlers(allow_write)),
    ):
        schemas.update(module_schemas)
        handlers.update(module_handlers)

    @server.list_tools()
    async def _list_tools() -> list[Tool]:
        return [
            Tool(
                name=name,
                description=meta["description"],
                inputSchema=meta["inputSchema"],
                annotations=ToolAnnotations(
                    readOnlyHint=meta.get("annotations", {}).get("readOnlyHint", True),
                    destructiveHint=meta.get("annotations", {}).get("destructiveHint", True),
                    idempotentHint=meta.get("annotations", {}).get("idempotentHint", False),
                    openWorldHint=meta.get("annotations", {}).get("openWorldHint", True),
                ),
            )
            for name, meta in schemas.items()
        ]

    @server.call_tool()
    async def _call_tool(name: str, arguments: dict[str, Any] | None) -> CallToolResult:
        args: dict[str, Any] = arguments or {}
        with contextlib.suppress(Exception):  # analytics must never break a tool call
            capture_event("mcp_tool_call", {"tool": name, "args": args})

        handler = handlers.get(name)
        if handler is None:
            return _error_result(
                name,
                f"unknown tool: {name!r}",
            )

        try:
            result = handler(args)
            if inspect.isawaitable(result):
                result = await result
        except Exception as exc:  # noqa: BLE001 - envelope all failures
            return _error_result(name, str(exc))

        return _normalize_result(result)

    return server


def _error_result(tool: str, error: str) -> CallToolResult:
    """Build an error ``CallToolResult`` envelope (ok=False)."""
    payload: dict[str, Any] = {
        "ok": False,
        "tool": tool,
        "error": error,
    }
    return CallToolResult(
        content=[TextContent(type="text", text=json.dumps(payload, default=str))],
        structuredContent=payload,
    )


def _normalize_result(result: Any) -> CallToolResult:
    """Normalize a handler return value into a ``CallToolResult``.

    All tool handlers now return ``ToolResult``. This function also accepts
    ``CallToolResult`` (for backward compat) and falls back to wrapping
    unexpected types as plain text.
    """
    if isinstance(result, CallToolResult):
        return result

    if isinstance(result, ToolResult):
        payload = result.model_dump()
        return CallToolResult(
            content=[TextContent(type="text", text=result.model_dump_json())],
            structuredContent=payload,
        )

    # Fallback: wrap any unexpected type as plain text.
    return CallToolResult(
        content=[TextContent(type="text", text=json.dumps(result, default=str))],
    )


def run_mcp_server(allow_write: bool = False) -> None:
    """Build the MCP server and run it over stdio until stdin closes.

    The stdio transport is anyio-based and must not run under
    :mod:`PySide6.QtAsyncio` (see the module docstring for the details), so the
    asyncio loop is driven by :func:`anyio.run` on the calling — main — thread,
    the same thread that owns ``QGuiApplication``. Qt events are pumped from
    within the loop so controller timers and queued signal deliveries keep
    progressing while MCP requests are served.

    Blocks until the client closes stdin, then returns so the caller can clean
    up and exit.
    """
    capture_event(
        "mcp_server_start",
        {
            "allow_write": allow_write,
            # Recorded so a client that gets no answer can tell which loop the
            # transport ran on (see ADR-0040) without re-reading the source.
            "transport": "anyio",
            "qt_pump_interval_s": _QT_PUMP_INTERVAL_S,
        },
    )

    server = create_mcp_server(allow_write)

    # ``anyio.run`` runs the coroutine on a fresh asyncio loop. No Qt event loop
    # is entered here; ``_pump_qt_events`` keeps Qt alive from inside asyncio.
    anyio.run(_run_stdio_with_qt_pump, server)


async def _run_stdio(server: Server[Any]) -> None:
    """Run the server over the stdio transport until stdin closes."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


async def _run_stdio_with_qt_pump(server: Server[Any]) -> None:
    """Run the stdio transport while pumping Qt events on the same thread."""
    async with anyio.create_task_group() as tg:
        tg.start_soon(_pump_qt_events)
        try:
            await _run_stdio(server)
        finally:
            tg.cancel_scope.cancel()


async def _pump_qt_events() -> None:
    """Process pending Qt events until cancelled.

    The MCP stdio loop owns the main thread, so nothing else would deliver Qt
    events (timers, queued connections, ``QEventLoop`` work posted by dumb
    controller operations). We drain them opportunistically. Failures are
    swallowed: Qt event pumping is best-effort and must never take the MCP
    server down.
    """
    while True:
        try:
            from PySide6.QtCore import QCoreApplication

            app = QCoreApplication.instance()
            if app is not None:
                app.processEvents()
        except Exception:  # noqa: BLE001 - pumping is best-effort only
            pass
        await anyio.sleep(_QT_PUMP_INTERVAL_S)


# ---------------------------------------------------------------------------
# Lightweight (no-Qt) variant — for cross-process Win32 tools only
# ---------------------------------------------------------------------------


def create_mcp_server_light() -> Server[Any]:
    """Construct a lightweight MCP server with only cross-process GUI tools.

    Registers only ``screenshot`` and ``gui`` tool modules — these use raw
    Win32 API (``PrintWindow``, ``SetCursorPos``, ``SendInput``, etc.) and
    file-based IPC for navigation. They require **no** ``QGuiApplication``,
    ``AppController``, or Qt event loop, so this server starts instantly
    and never hangs.

    Returns:
        A fully-wired :class:`Server` instance ready to ``run()`` over stdio.
    """
    server: Server[Any] = Server("SkillManager-Light")

    from skill_manager.mcp.tools.gui import (
        TOOL_SCHEMAS as GUI_SCHEMAS,
        get_handlers as gui_handlers,
    )
    from skill_manager.mcp.tools.screenshot import (
        TOOL_SCHEMAS as SCREENSHOT_SCHEMAS,
        get_handlers as screenshot_handlers,
    )

    schemas: dict[str, dict[str, Any]] = {}
    handlers: dict[str, Any] = {}
    for module_schemas, module_handlers in (
        (SCREENSHOT_SCHEMAS, screenshot_handlers()),
        (GUI_SCHEMAS, gui_handlers()),
    ):
        schemas.update(module_schemas)
        handlers.update(module_handlers)

    @server.list_tools()
    async def _list_tools() -> list[Tool]:
        return [
            Tool(
                name=name,
                description=meta["description"],
                inputSchema=meta["inputSchema"],
            )
            for name, meta in schemas.items()
        ]

    @server.call_tool()
    async def _call_tool(name: str, arguments: dict[str, Any] | None) -> CallToolResult:
        args: dict[str, Any] = arguments or {}
        handler = handlers.get(name)
        if handler is None:
            return _error_result(name, f"unknown tool: {name!r}")
        try:
            result = handler(args)
            if inspect.isawaitable(result):
                result = await result
        except Exception as exc:
            return _error_result(name, str(exc))
        return _normalize_result(result)

    return server


def run_mcp_server_light() -> None:
    """Run the lightweight (no-Qt) MCP server over stdio.

    Uses a pure asyncio event loop on the main thread. No ``QGuiApplication``,
    no ``AppController``, no hotkey system — instant startup.

    Available tools: ``sm_screenshot``, ``sm_mouse_move``, ``sm_mouse_click``,
    ``sm_type_text``, ``sm_get_window_info``, ``sm_toggle_debug_overlay``,
    ``sm_get_window_rect``.
    """
    server = create_mcp_server_light()
    anyio.run(_run_stdio, server)


__all__ = [
    "create_mcp_server",
    "create_mcp_server_light",
    "run_mcp_server",
    "run_mcp_server_light",
]
