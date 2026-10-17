"""Unit tests for the ``sm_accessibility_audit`` MCP tool handler and bridge.

These tests exercise the handler entry point directly while monkeypatching the
bridge function. They never boot Qt or construct ``AppController``.
"""

from __future__ import annotations

from typing import Any

import pytest

from skill_manager.mcp.models import ToolResult
from skill_manager.mcp.tools import accessibility as acc_mod


def test_accessibility_audit_returns_result(monkeypatch: pytest.MonkeyPatch) -> None:
    """sm_accessibility_audit returns the bridge's audit result."""
    fake = {
        "ok": True,
        "element_count": 25,
        "issue_count": 2,
        "issues": [
            {
                "object_name": "save_button",
                "class_name": "QPushButton",
                "issue_type": "missing_name",
                "severity": "high",
                "description": "Interactive element 'save_button' (QPushButton) has no Accessible name.",
                "suggestion": "Set Accessible.name on this element.",
            },
            {
                "object_name": "title_label",
                "class_name": "QLabel",
                "issue_type": "missing_name",
                "severity": "medium",
                "description": "Interactive element 'title_label' (QLabel) has no Accessible name.",
                "suggestion": "Set Accessible.name on this element.",
            },
        ],
        "error": None,
    }
    monkeypatch.setattr(
        acc_mod,
        "_bridge_audit_accessibility",
        lambda max_depth=10: fake,
    )

    result = acc_mod.get_handlers()["sm_accessibility_audit"]({"max_depth": 5})

    assert isinstance(result, ToolResult)
    assert result.ok is True
    assert result.tool == "sm_accessibility_audit"
    assert result.data == fake
    assert result.data["issue_count"] == 2


def test_accessibility_audit_forwards_max_depth(monkeypatch: pytest.MonkeyPatch) -> None:
    """sm_accessibility_audit forwards max_depth to the bridge."""
    captured: dict[str, Any] = {}

    def _fake(max_depth: int = 10) -> dict[str, Any]:
        captured["max_depth"] = max_depth
        return {
            "ok": True,
            "element_count": 0,
            "issue_count": 0,
            "issues": [],
            "error": None,
        }

    monkeypatch.setattr(acc_mod, "_bridge_audit_accessibility", _fake)

    acc_mod.get_handlers()["sm_accessibility_audit"]({"max_depth": 15})
    assert captured["max_depth"] == 15


def test_accessibility_audit_defaults_max_depth(monkeypatch: pytest.MonkeyPatch) -> None:
    """sm_accessibility_audit defaults max_depth to 10."""
    captured: dict[str, Any] = {}

    def _fake(max_depth: int = 10) -> dict[str, Any]:
        captured["max_depth"] = max_depth
        return {
            "ok": True,
            "element_count": 0,
            "issue_count": 0,
            "issues": [],
            "error": None,
        }

    monkeypatch.setattr(acc_mod, "_bridge_audit_accessibility", _fake)

    acc_mod.get_handlers()["sm_accessibility_audit"]({})
    assert captured["max_depth"] == 10


def test_accessibility_audit_degrades_on_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """sm_accessibility_audit returns ok=False when the bridge reports failure."""
    monkeypatch.setattr(
        acc_mod,
        "_bridge_audit_accessibility",
        lambda max_depth=10: {
            "ok": False,
            "element_count": 0,
            "issue_count": 0,
            "issues": [],
            "error": "qml_engine_unavailable",
        },
    )

    result = acc_mod.get_handlers()["sm_accessibility_audit"]({"max_depth": 10})

    assert result.ok is False
    assert result.error is not None
    assert "qml_engine_unavailable" in result.error


def test_accessibility_audit_exception_becomes_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """A bridge exception degrades to a ToolResult error envelope."""
    monkeypatch.setattr(
        acc_mod,
        "_bridge_audit_accessibility",
        lambda max_depth=10: (_ for _ in ()).throw(RuntimeError("boom")),
    )

    result = acc_mod.get_handlers()["sm_accessibility_audit"]({"max_depth": 10})

    assert result.ok is False
    assert result.error is not None
    assert "boom" in result.error


def test_accessibility_audit_tool_schema_declared() -> None:
    """sm_accessibility_audit is declared in TOOL_SCHEMAS with valid input schema."""
    assert "sm_accessibility_audit" in acc_mod.TOOL_SCHEMAS
    schema = acc_mod.TOOL_SCHEMAS["sm_accessibility_audit"]
    assert schema["description"]
    assert schema["inputSchema"]["type"] == "object"
    assert "max_depth" in schema["inputSchema"]["properties"]
    assert schema["annotations"]["readOnlyHint"] is True
