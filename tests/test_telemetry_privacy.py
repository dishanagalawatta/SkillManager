"""Telemetry privacy guards.

These tests lock in two invariants that were violated before:

1. MCP tool telemetry must never forward raw arguments, local paths,
   free-form queries, or user-authored content (``capture_mcp_tool_call``
   enforces this centrally).
2. The repository must never track ``.env`` (it holds live credentials) or
   commit a PostHog project token.

They are pure/cheap and do not touch Qt or the network.
"""

from __future__ import annotations

import pathlib
import re
import subprocess

import pytest

import skill_manager
from skill_manager.core import analytics

_MCP_DIR = pathlib.Path(skill_manager.__file__).resolve().parent / "mcp"
_REPO_ROOT = pathlib.Path(skill_manager.__file__).resolve().parents[2]

# Keys that must never reach analytics from an MCP call site.
_BLOCKED = (
    "args",
    "query",
    "path",
    "pattern",
    "skill_id",
    "source_path",
    "target",
    "content",
    "body",
    "body_content",
    "raw_content",
    "text",
    "project_label",
)


def test_capture_mcp_tool_call_drops_sensitive_keys_and_non_scalars(monkeypatch):
    captured: dict = {}
    monkeypatch.setattr(
        analytics,
        "capture_event",
        lambda event, properties=None: captured.update({"event": event, "properties": properties}),
    )

    analytics.capture_mcp_tool_call(
        "mcp_tool_call",
        "sm_example",
        {
            "args": {"text": "typed secret"},
            "query": "find my password",
            "path": "/home/someone/private",
            "pattern": "api_key",
            "skill_id": "/home/someone/.agents/skills/x",
            "source_path": "/home/someone/src",
            "target": "/home/someone/project",
            "content": "skill body",
            "body": "skill body",
            "body_content": "skill body",
            "raw_content": "skill body",
            "text": "typed secret",
            "project_label": "/home/someone/project",
            "limit": 5,
            "enabled": True,
            "duration_s": 1.5,
            "name": "safe-identifier",
        },
    )

    assert captured["event"] == "mcp_tool_call"
    props = captured["properties"]
    assert props["tool"] == "sm_example"
    for key in _BLOCKED:
        assert key not in props, f"{key!r} must never be forwarded"
    # Only scalars survive.
    assert props["limit"] == 5
    assert props["enabled"] is True
    assert props["duration_s"] == 1.5
    assert props["name"] == "safe-identifier"
    # No forwarded string may carry an absolute path or the typed secret.
    assert not any(isinstance(v, str) and ("/home/" in v or "secret" in v) for v in props.values())


def test_no_mcp_call_site_forwards_raw_arguments():
    """Regression guard: no MCP module may capture raw ``args`` again."""
    offenders: list[str] = []
    for path in sorted(_MCP_DIR.rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        if re.search(r'capture_event\(\s*"mcp_(?:tool_call|write_attempt)"', text):
            offenders.append(str(path.relative_to(_MCP_DIR)))
        if '"args": args' in text:
            offenders.append(str(path.relative_to(_MCP_DIR)))
    assert not offenders, f"raw MCP arguments must not be captured: {offenders}"


def test_sentry_scrubber_removes_identifying_data():
    from skill_manager.bootstrap import _scrub_sentry_event

    event = {
        "message": "boom",
        "request": {"url": "https://example/api?token=leak"},
        "user": {"email": "someone@example.com"},
        "breadcrumbs": {"values": [{"message": "x", "data": {"path": "/home/someone/secret"}}]},
    }
    scrubbed = _scrub_sentry_event(event, {})
    assert "request" not in scrubbed
    assert "user" not in scrubbed
    assert scrubbed["breadcrumbs"]["values"][0] == {"message": "x"}
    assert scrubbed["message"] == "boom"


def _git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(_REPO_ROOT), *args],
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.mark.skipif(
    _git("rev-parse", "--is-inside-work-tree").returncode != 0,
    reason="not inside a git work tree",
)
def test_env_is_not_tracked():
    """.env holds live credentials and must never be committed."""
    tracked = _git("ls-files", "--error-unmatch", ".env")
    assert tracked.returncode != 0, ".env must not be tracked by git"


@pytest.mark.skipif(
    _git("rev-parse", "--is-inside-work-tree").returncode != 0,
    reason="not inside a git work tree",
)
def test_no_committed_posthog_token():
    """No tracked file may contain a live PostHog project token (``phc_...``)."""
    found = _git("grep", "-nE", r"phc_[A-Za-z0-9]{20,}")
    assert found.stdout.strip() == "", f"committed PostHog token detected:\n{found.stdout}"
