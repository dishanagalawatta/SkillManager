"""Shared telemetry for the MCP bridge package (leaf module).

Provides the bridge-wide ``logger``, the analytics ``_log_call`` helper, and
re-exports ``get_diagnostic_logger`` for the capture/state modules. No imports
from sibling bridge modules.
"""

from __future__ import annotations

import contextlib
import logging

from skill_manager.core.analytics import capture_event
from skill_manager.core.diagnostics import (
    get_diagnostic_logger as get_diagnostic_logger,
)

# Keep the original logger name so logging configuration that references
# "skill_manager.mcp.bridge" keeps working after the package split.
logger = logging.getLogger("skill_manager.mcp.bridge")


def _log_call(fn: str) -> None:
    """Record a bridge call via analytics (never raises)."""
    with contextlib.suppress(Exception):
        capture_event("mcp_bridge_call", {"fn": fn})
