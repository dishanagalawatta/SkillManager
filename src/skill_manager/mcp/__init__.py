"""SkillManager MCP server package.

Public surface for launching the MCP stdio server from the application entry
point (``skill_manager.app.main``).
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

from skill_manager.mcp.server import (
    create_mcp_server,
    create_mcp_server_light,
    run_mcp_server,
    run_mcp_server_light,
)

__all__ = [
    "create_mcp_server",
    "create_mcp_server_light",
    "run_mcp_server",
    "run_mcp_server_light",
    "start_mcp_if_requested",
]


def start_mcp_if_requested(argv: list[str] | None = None) -> bool:
    """If ``--mcp`` is present in *argv*, run the MCP server and return ``True``.

    Parses ``--mcp`` and ``--mcp-allow-write`` from the argument list. When
    ``--mcp`` is set the MCP stdio server is started (blocking until stdin
    closes) and this function returns ``True`` so the caller can skip the
    normal GUI launch. When ``--mcp`` is absent it returns ``False`` and the
    caller proceeds with the GUI path unchanged.

    Args:
        argv: Argument list to parse. Defaults to ``sys.argv``.

    Returns:
        ``True`` if MCP mode was requested and the server ran; ``False``
        otherwise.
    """
    args = list(sys.argv if argv is None else argv)
    if "--mcp" not in args:
        return False

    allow_write = "--mcp-allow-write" in args
    run_mcp_server(allow_write=allow_write)
    return True
