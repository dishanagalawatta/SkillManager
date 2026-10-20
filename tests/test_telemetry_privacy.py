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

import os
import pathlib
import re
import subprocess
import sys
import types

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
    "name",
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
            "name": "acme-internal-deploy",
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
    # No forwarded string may carry an absolute path or the typed secret.
    assert not any(
        isinstance(v, str) and ("/home/" in v or "secret" in v or "acme" in v)
        for v in props.values()
    )


def test_mcp_write_attempt_never_forwards_the_skill_name(monkeypatch):
    """Regression guard: ``sm_create_skill``'s ``name`` is user content.

    It reached analytics before, unlike every other identifier key
    (``skill_id``, ``path``, ``query``, ...). The allowlist now drops it.
    """
    captured: dict = {}
    monkeypatch.setattr(
        analytics,
        "capture_event",
        lambda event, properties=None: captured.update({"event": event, "properties": properties}),
    )

    analytics.capture_mcp_tool_call(
        "mcp_write_attempt",
        "sm_create_skill",
        {"allowed": True, "name": "acme-internal-deploy"},
    )

    assert captured["event"] == "mcp_write_attempt"
    props = captured["properties"]
    assert props["tool"] == "sm_create_skill"
    assert props["allowed"] is True
    assert "name" not in props
    assert not any(isinstance(v, str) and "acme" in v for v in props.values())


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


def test_no_tool_module_emits_mcp_tool_call_directly():
    """Regression guard: the server wrapper owns ``mcp_tool_call``.

    Every tool module used to capture its own ``mcp_tool_call`` in addition to
    the wrapper, so each invocation produced two events and the properties
    landed on a different record than the count.
    """
    offenders: list[str] = []
    for path in sorted(_MCP_DIR.rglob("*.py")):
        if path.name == "server.py":
            continue
        if 'capture_mcp_tool_call("mcp_tool_call"' in path.read_text(encoding="utf-8"):
            offenders.append(str(path.relative_to(_MCP_DIR)))
    assert not offenders, f"tool modules must not emit mcp_tool_call themselves: {offenders}"


def test_add_mcp_tool_properties_applies_the_allowlist_and_is_scoped_to_the_call():
    """Handlers contribute through the collector, not by capturing."""
    token = analytics.begin_mcp_tool_call()
    analytics.add_mcp_tool_properties(
        {
            "query": "find my password",
            "path": "/home/someone/private",
            "pattern": "api_key",
            "skill_id": "/home/someone/.agents/skills/x",
            "content": "skill body",
            "name": "acme-internal-deploy",
            "tool": "spoofed",
            "nested": {"a": 1},
            "limit": 5,
            "enabled": True,
        }
    )
    properties = analytics.end_mcp_tool_call(token)

    assert properties == {"limit": 5, "enabled": True}
    # Outside a server call the collector is a no-op, never an error.
    assert analytics.add_mcp_tool_properties(limit=9) is None
    assert analytics._mcp_tool_properties.get() is None


def test_mcp_server_emits_exactly_one_tool_call_event(monkeypatch):
    """One invocation → one event, carrying handler properties and outcome."""
    import anyio
    from mcp import types as mcp_types

    from skill_manager.mcp import server as mcp_server

    captured: list[tuple[str, str, dict]] = []
    monkeypatch.setattr(
        mcp_server,
        "capture_mcp_tool_call",
        lambda event, tool, properties=None: captured.append((event, tool, properties or {})),
    )

    server = mcp_server.create_mcp_server(allow_write=False)
    handler = server.request_handlers[mcp_types.CallToolRequest]
    request = mcp_types.CallToolRequest(
        params=mcp_types.CallToolRequestParams(
            name="sm_get_diagnostics",
            arguments={"limit": 3},
        )
    )
    anyio.run(handler, request)

    assert len(captured) == 1, f"expected one mcp_tool_call event, got {captured}"
    event, tool, properties = captured[0]
    assert event == "mcp_tool_call"
    assert tool == "sm_get_diagnostics"
    assert properties["limit"] == 3
    assert properties["ok"] is True
    assert isinstance(properties["duration_ms"], int)


def test_mcp_server_reports_failed_calls_without_the_error_text(monkeypatch):
    """``ok`` is recorded; the exception message (paths!) never is."""
    import anyio
    from mcp import types as mcp_types

    from skill_manager.mcp import server as mcp_server

    captured: list[dict] = []
    monkeypatch.setattr(
        mcp_server,
        "capture_mcp_tool_call",
        lambda event, tool, properties=None: captured.append(properties or {}),
    )

    server = mcp_server.create_mcp_server(allow_write=False)
    handler = server.request_handlers[mcp_types.CallToolRequest]
    request = mcp_types.CallToolRequest(
        params=mcp_types.CallToolRequestParams(name="sm_not_a_tool", arguments={})
    )
    anyio.run(handler, request)

    assert len(captured) == 1
    assert captured[0]["ok"] is False
    assert "sm_not_a_tool" not in captured[0].values()


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


# ---------------------------------------------------------------------------
# Exception payloads and credential loading
# ---------------------------------------------------------------------------


def test_scrub_posthog_event_redacts_paths_and_source_context():
    """Autocaptured exceptions must not ship absolute paths or source lines."""
    event = {
        "event": "$exception",
        "properties": {
            "$exception_list": [
                {
                    "type": "ValueError",
                    "value": (
                        "Clone path exists but is not an empty git checkout: /home/someone/proj"
                    ),
                    "stacktrace": {
                        "type": "raw",
                        "frames": [
                            {
                                "filename": "skill_manager/core/skill_packages/updater.py",
                                "abs_path": (
                                    "/home/someone/repo/src/skill_manager/"
                                    "core/skill_packages/updater.py"
                                ),
                                "context_line": "raise ValueError(f'...{path}')",
                                "pre_context": ["secret = 'x'"],
                                "post_context": ["secret = 'y'"],
                                "function": "_clone",
                                "lineno": 72,
                            }
                        ],
                    },
                }
            ],
            "tool": "sm_example",
        },
    }

    scrubbed = analytics._scrub_posthog_event(event)
    exception = scrubbed["properties"]["$exception_list"][0]

    assert "/home/someone" not in exception["value"]
    assert "<path>" in exception["value"]

    frame = exception["stacktrace"]["frames"][0]
    for key in ("abs_path", "context_line", "pre_context", "post_context", "vars"):
        assert key not in frame, f"{key!r} leaks source/paths"
    # Debugging signal survives: bare filename, function, line.
    assert frame["filename"] == "updater.py"
    assert frame["function"] == "_clone"
    assert frame["lineno"] == 72

    # Non-path telemetry is left alone.
    assert scrubbed["properties"]["tool"] == "sm_example"
    assert exception["type"] == "ValueError"


def test_scrub_posthog_event_survives_odd_payloads():
    """A malformed event must never raise — the SDK fails open, not closed."""
    for event in (
        {},
        {"properties": None},
        {"properties": {"$exception_list": None}},
        {"properties": {"$exception_list": ["not-a-dict", 1, None]}},
        {"properties": {"$exception_list": [{"stacktrace": ["bad"]}]}},
        {"properties": {"$exception_list": [{"stacktrace": {"frames": ["bad"]}}]}},
    ):
        assert analytics._scrub_posthog_event(dict(event)) is not None


def test_env_loading_never_reads_the_working_directory(tmp_path, monkeypatch):
    """Regression guard for the CWD ``.env`` hijack.

    Launching from a project directory used to import that project's ``.env``:
    unrelated secrets, and a ``POSTHOG_HOST`` able to redirect telemetry.
    """
    (tmp_path / ".env").write_text(
        "HOSTILE_CWD_MARKER=1\nPOSTHOG_HOST=https://attacker.example\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    before = dict(os.environ)
    try:
        analytics._load_env()
        assert "HOSTILE_CWD_MARKER" not in os.environ
        assert os.environ.get("POSTHOG_HOST") != "https://attacker.example"
    finally:
        os.environ.clear()
        os.environ.update(before)


def test_posthog_client_is_built_with_the_scrubber(monkeypatch):
    """The scrubber and the no-code-variables setting must stay wired up."""
    captured: dict = {}

    class FakePosthog:
        def __init__(self, *args, **kwargs):
            captured.update(kwargs)

        def shutdown(self):  # pragma: no cover - not called here
            pass

    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.delenv("SKILL_MANAGER_TESTING", raising=False)
    monkeypatch.setenv("POSTHOG_PROJECT_TOKEN", "phc_test_token")
    monkeypatch.setenv("POSTHOG_HOST", "https://example.invalid")
    monkeypatch.setitem(sys.modules, "posthog", types.SimpleNamespace(Posthog=FakePosthog))
    monkeypatch.setattr(analytics.atexit, "register", lambda *a, **k: None)

    assert analytics.init_posthog() is not None
    assert captured["before_send"] is analytics._scrub_posthog_event
    assert captured["capture_exception_code_variables"] is False
    assert captured["enable_exception_autocapture"] is True
