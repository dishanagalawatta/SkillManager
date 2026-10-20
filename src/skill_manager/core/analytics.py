"""PostHog analytics integration for Skill Manager."""

import atexit
import contextlib
import contextvars
import json
import os
import re
import uuid
from pathlib import Path
from typing import Any

#: ``.env`` shipped with a source checkout (``<repo>/src/skill_manager/core/`` → repo root).
_REPO_ROOT_ENV = Path(__file__).resolve().parents[3] / ".env"


def _env_file_candidates() -> list[Path]:
    """Return the ``.env`` locations to try, highest priority first.

    Deliberately *not* ``load_dotenv()`` without a path: that searches upward
    from the current working directory, and SkillManager is normally launched
    from inside a project directory. Doing so imported that project's ``.env``
    wholesale — its unrelated secrets, plus any ``POSTHOG_HOST`` able to
    redirect this app's telemetry (and project token) to an arbitrary host.
    """
    candidates: list[Path] = []
    # A packaged/user install owns this file, so it takes precedence.
    try:
        from skill_manager.core.config import DATA_DIR

        candidates.append(Path(DATA_DIR) / ".env")
    except Exception:
        pass
    candidates.append(_REPO_ROOT_ENV)
    return candidates


def _load_env() -> None:
    """Load credentials from an app-owned ``.env`` file — never from the CWD."""
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    for path in _env_file_candidates():
        if path.is_file():
            with contextlib.suppress(Exception):
                load_dotenv(dotenv_path=path, override=False)
            return


_load_env()


def get_or_create_device_id() -> str:
    """Return a persistent device ID stored in the app data directory."""
    from skill_manager.core.config import DATA_DIR

    device_id_file = DATA_DIR / "device_id.json"

    if device_id_file.exists():
        try:
            data = json.loads(device_id_file.read_text(encoding="utf-8"))
            if data.get("device_id"):
                return data["device_id"]
        except Exception:
            pass

    device_id = f"device_{uuid.uuid4().hex}"
    with contextlib.suppress(Exception):
        device_id_file.write_text(json.dumps({"device_id": device_id}), encoding="utf-8")
    return device_id


#: Absolute POSIX/Windows paths and ``~``-relative paths.
_ABSOLUTE_PATH_RE = re.compile(r"(?:[A-Za-z]:[\\/]|/)[^\s'\"]+|~[\\/][^\s'\"]*")


def _redact_paths(text: str) -> str:
    """Replace absolute filesystem paths (and thus the OS username) with a marker."""
    return _ABSOLUTE_PATH_RE.sub("<path>", text)


def _scrub_posthog_event(event: dict) -> dict:
    """Strip filesystem paths and source context from an outgoing event.

    Mirrors ``_scrub_sentry_event`` in :mod:`skill_manager.bootstrap`, which
    PostHog previously had no equivalent of. Exception autocapture is why this
    exists: ``enable_exception_autocapture=True`` installs global ``sys`` and
    ``threading`` excepthooks, so stack traces and exception messages leave the
    machine *without* passing through :func:`capture_mcp_tool_call`'s allowlist.
    Messages routinely embed absolute paths (see
    ``core/skill_packages/updater.py``) and skill/project names.
    """
    try:
        properties = event.get("properties")
        if not isinstance(properties, dict):
            return event
        for exception in properties.get("$exception_list") or []:
            if not isinstance(exception, dict):
                continue
            value = exception.get("value")
            if isinstance(value, str):
                exception["value"] = _redact_paths(value)
            stacktrace = exception.get("stacktrace")
            frames = stacktrace.get("frames") if isinstance(stacktrace, dict) else None
            for frame in frames or []:
                if not isinstance(frame, dict):
                    continue
                for key in ("abs_path", "context_line", "pre_context", "post_context", "vars"):
                    frame.pop(key, None)
                # Keep the module/file name for debugging, drop the directory tree.
                filename = frame.get("filename")
                if isinstance(filename, str):
                    frame["filename"] = filename.replace("\\", "/").rsplit("/", 1)[-1]
    except Exception:
        pass
    return event


def _test_run() -> bool:
    """True while running under pytest (see ``tests/conftest.py``)."""
    return bool(os.getenv("PYTEST_CURRENT_TEST") or os.getenv("SKILL_MANAGER_TESTING") == "1")


def _user_disabled_telemetry() -> bool:
    """True when the user switched telemetry off in Settings.

    Read straight from the persisted config rather than from
    ``UIController``, so the decision holds for the very first event —
    ``app_opened`` — without depending on Qt or controller startup order.
    """
    try:
        from skill_manager.core.config import DATA_DIR

        record = json.loads((Path(DATA_DIR) / "config.json").read_text(encoding="utf-8"))
        return record.get("ui_state", {}).get("telemetry_enabled", True) is False
    except Exception:
        return False


def _build_client():
    """Construct the PostHog client, or ``None`` when unconfigured."""
    token = os.getenv("POSTHOG_PROJECT_TOKEN")
    host = os.getenv("POSTHOG_HOST")
    if not token or not host:
        return None
    try:
        from posthog import Posthog

        return Posthog(
            token,
            host=host,
            enable_exception_autocapture=True,
            before_send=_scrub_posthog_event,
            # Explicit: GeoIP enrichment must stay off so events cannot be
            # traced to a network. True is the current SDK default; pinning it
            # guards against a future default flip, like the setting below.
            disable_geoip=True,
            # Explicit: local variable *values* must never be attached to
            # autocaptured frames. False is the SDK default; pinning it guards
            # against a future default flip.
            capture_exception_code_variables=False,
        )
    except Exception:
        return None


def init_posthog():
    # Safeguard: Never initialize a real client during tests.
    # This prevents background threads from hanging pytest on exit.
    if _test_run():
        return None
    if _user_disabled_telemetry():
        return None
    client = _build_client()
    if client is not None:
        atexit.register(client.shutdown)
    return client


def set_enabled(enabled: bool) -> None:
    """Apply the Settings telemetry toggle without requiring a restart.

    Disabling tears the client down immediately, so no further event can
    leave the machine; enabling rebuilds it when credentials exist.
    """
    global _posthog
    if not enabled:
        if _posthog is not None:
            with contextlib.suppress(Exception):
                _posthog.shutdown()
            _posthog = None
        return
    if _posthog is None and not _test_run():
        client = _build_client()
        if client is not None:
            atexit.register(client.shutdown)
            _posthog = client


_posthog = init_posthog()
_device_id: str | None = None


def get_device_id() -> str:
    global _device_id
    if _device_id is None:
        _device_id = get_or_create_device_id()
    return _device_id


def capture_event(event: str, properties: dict | None = None) -> None:
    """Capture a PostHog analytics event. Safe to call if PostHog is not configured."""
    if _posthog is None:
        return
    with contextlib.suppress(Exception):
        _posthog.capture(
            distinct_id=get_device_id(),
            event=event,
            properties=properties or {},
        )


def capture_exception(exc: Exception) -> None:
    """Capture an exception for PostHog error tracking."""
    if _posthog is None:
        return
    with contextlib.suppress(Exception):
        _posthog.capture_exception(exc, distinct_id=get_device_id())


# ---------------------------------------------------------------------------
# MCP tool-call telemetry (privacy allowlist)
# ---------------------------------------------------------------------------
#
# MCP tool arguments can carry user-authored content, free-form search
# queries, and absolute filesystem paths. None of that may leave the machine,
# so every ``mcp_tool_call`` / ``mcp_write_attempt`` event goes through
# ``capture_mcp_tool_call``. One allowlist — not each call site — decides what
# is safe to send.
_MCP_TELEMETRY_BLOCKED_KEYS = frozenset(
    {
        "args",
        "path",
        "pattern",
        "query",
        "skill_id",
        # User-authored skill name (``sm_create_skill``): an identifier of the
        # same kind as ``skill_id``, so it is dropped for the same reason.
        "name",
        "source_path",
        "target",
        "content",
        "body",
        "body_content",
        "raw_content",
        "text",
        "project_label",
    }
)
_MCP_TELEMETRY_SCALARS = (bool, int, float, str)

#: Properties contributed by an MCP tool handler for the *current* call.
#: The server wrapper owns the single ``mcp_tool_call`` emission, so handlers
#: contribute instead of capturing: previously the wrapper and every handler
#: both captured, doubling each event and splitting its properties across two
#: records.
_mcp_tool_properties: contextvars.ContextVar[dict | None] = contextvars.ContextVar(
    "mcp_tool_properties", default=None
)


def begin_mcp_tool_call() -> contextvars.Token:
    """Start collecting properties for one MCP tool call."""
    return _mcp_tool_properties.set({})


def end_mcp_tool_call(token: contextvars.Token) -> dict:
    """Stop collecting and return the properties for the finished call."""
    properties = _mcp_tool_properties.get() or {}
    _mcp_tool_properties.reset(token)
    return properties


def add_mcp_tool_properties(properties: dict | None = None, **extra: Any) -> None:
    """Record allowlisted scalars for the in-flight ``mcp_tool_call`` event.

    Applies the same allowlist as :func:`capture_mcp_tool_call`, so a handler
    may pass its raw arguments without leaking user content, paths, or
    free-form queries. No-op when no server call is collecting (for example a
    handler invoked directly in a test).
    """
    current = _mcp_tool_properties.get()
    if current is None:
        return
    merged = dict(properties or {})
    merged.update(extra)
    for key, value in merged.items():
        if key == "tool" or key in _MCP_TELEMETRY_BLOCKED_KEYS:
            continue
        if isinstance(value, _MCP_TELEMETRY_SCALARS):
            current[key] = value


def capture_mcp_tool_call(event: str, tool: str, properties: dict | None = None) -> None:
    """Capture an MCP tool event with a privacy-safe, allowlisted payload.

    Free-form or path-bearing fields (``args``, ``query``, ``path``,
    ``pattern``, ``skill_id``, ``name``, ``content``, ``text``, ...) are
    dropped, and only JSON scalar values are forwarded, so tool arguments can
    never leak user content or local paths into analytics.
    """
    safe: dict = {"tool": str(tool)}
    for key, value in (properties or {}).items():
        if key in _MCP_TELEMETRY_BLOCKED_KEYS:
            continue
        if isinstance(value, _MCP_TELEMETRY_SCALARS):
            safe[key] = value
    capture_event(event, safe)


def shutdown() -> None:
    """Flush all queued PostHog events and shut down the client."""
    if _posthog is not None:
        with contextlib.suppress(Exception):
            _posthog.shutdown()
