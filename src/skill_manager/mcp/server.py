"""MCP server entry point for SkillManager.

Builds a low-level :class:`mcp.server.Server`, wires every tool module, and
runs it over stdio. The server is asyncio-based; SkillManager also owns a Qt
event loop. We drive a *combined* loop with :mod:`PySide6.QtAsyncio` so the MCP
stdio transport and Qt coexist without either blocking the other, and without
Qt consuming stdin/stdout.

Tool modules (``build``, ``analyze``, ``monitor``, ``debug``, ``write``) own
their own ``list_tools`` / ``call_tool`` registration via decorators on the
passed :class:`Server` instance. This module only constructs the server and
delegates registration to each ``register_*_tools`` function — it does NOT
install its own handlers. Imports are performed lazily inside
:func:`create_mcp_server` so a sibling module that is not finished yet does not
break importing this package.
"""

from __future__ import annotations

import asyncio
import contextlib
import inspect
import json
import threading
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import CallToolResult, TextContent, Tool

from skill_manager.core.analytics import capture_event
from skill_manager.mcp.models import ToolResult


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

    from skill_manager.mcp.tools.analyze import (
        TOOL_SCHEMAS as ANALYZE_SCHEMAS,
        get_handlers as analyze_handlers,
    )
    from skill_manager.mcp.tools.build import (
        TOOL_SCHEMAS as BUILD_SCHEMAS,
        get_handlers as build_handlers,
    )
    from skill_manager.mcp.tools.debug import (
        TOOL_SCHEMAS as DEBUG_SCHEMAS,
        get_handlers as debug_handlers,
    )
    from skill_manager.mcp.tools.monitor import (
        TOOL_SCHEMAS as MONITOR_SCHEMAS,
        get_handlers as monitor_handlers,
    )
    from skill_manager.mcp.tools.screenshot import (
        TOOL_SCHEMAS as SCREENSHOT_SCHEMAS,
        get_handlers as screenshot_handlers,
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
        (MONITOR_SCHEMAS, monitor_handlers()),
        (DEBUG_SCHEMAS, debug_handlers()),
        (SCREENSHOT_SCHEMAS, screenshot_handlers()),
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

        return _normalize_result(name, result)

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


def _normalize_result(tool: str, result: Any) -> CallToolResult:
    """Normalize a handler return value into a ``CallToolResult``.

    Handlers may return a ``CallToolResult`` (analyze/monitor/debug via the
    server), a ``list[TextContent]`` (analyze handlers), a ``ToolResult``
    (monitor/debug/build/write), or a plain ``dict`` (build/write envelopes).
    """
    if isinstance(result, CallToolResult):
        return result

    if isinstance(result, list):
        # analyze handlers return list[TextContent]; wrap as-is.
        return CallToolResult(content=result)

    if isinstance(result, ToolResult):
        payload = result.model_dump()
        return CallToolResult(
            content=[TextContent(type="text", text=result.model_dump_json())],
            structuredContent=payload,
        )

    if isinstance(result, dict):
        return CallToolResult(
            content=[TextContent(type="text", text=json.dumps(result, default=str))],
            structuredContent=result,
        )

    # Fallback: wrap any other scalar as text.
    payload = {"ok": True, "tool": tool, "data": result}
    return CallToolResult(
        content=[TextContent(type="text", text=json.dumps(payload, default=str))],
        structuredContent=payload,
    )


def run_mcp_server(allow_write: bool = False) -> None:
    """Build the MCP server and run it over stdio, pumping the Qt event loop.

    SkillManager normally runs a Qt event loop (``app.exec()``). The MCP stdio
    server is asyncio-based. We use :mod:`PySide6.QtAsyncio` to drive a single
    combined loop: Qt's event loop pumps the asyncio loop, so the MCP stdio
    transport runs without blocking Qt and without Qt consuming stdin/stdout.

    If ``PySide6.QtAsyncio`` is unavailable we fall back to running the MCP
    server on a dedicated asyncio loop in a daemon thread, keeping the calling
    thread free for Qt.
    """
    capture_event("mcp_server_start", {"allow_write": allow_write})

    server = create_mcp_server(allow_write)

    try:
        from PySide6 import QtAsyncio  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001 - QtAsyncio may be absent on some builds
        qt_asyncio = None
    else:
        qt_asyncio = QtAsyncio

    if qt_asyncio is not None:
        # Combined Qt + asyncio loop. ``QtAsyncio.run`` installs a Qt-aware
        # asyncio policy and runs the coroutine on the Qt loop.
        qt_asyncio.run(_run_stdio(server))
        return

    # Fallback: dedicated asyncio loop in a daemon thread.
    _run_in_thread(server)


async def _run_stdio(server: Server[Any]) -> None:
    """Run the server over the stdio transport until stdin closes."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


def _run_in_thread(server: Server[Any]) -> None:
    """Run the MCP stdio server on its own asyncio loop in a daemon thread."""
    loop = asyncio.new_event_loop()

    def _pump() -> None:
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(_run_stdio(server))
        except (KeyboardInterrupt, asyncio.CancelledError):  # pragma: no cover
            pass
        finally:
            loop.close()

    thread = threading.Thread(target=_pump, daemon=True)
    thread.start()
    # Keep the calling (Qt) thread alive until the server thread finishes
    # (stdin closed) or the process exits.
    try:
        thread.join()
    except KeyboardInterrupt:  # pragma: no cover
        loop.call_soon_threadsafe(loop.stop)


__all__ = ["create_mcp_server", "run_mcp_server"]
