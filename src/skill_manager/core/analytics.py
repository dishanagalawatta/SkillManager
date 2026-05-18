"""PostHog analytics integration for Skill Manager."""

import atexit
import contextlib
import json
import os
import uuid


def _load_env() -> None:
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass


_load_env()


def _get_or_create_device_id() -> str:
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


def _init_posthog():
    token = os.getenv("POSTHOG_PROJECT_TOKEN")
    host = os.getenv("POSTHOG_HOST")
    if not token or not host:
        return None
    try:
        from posthog import Posthog

        client = Posthog(
            token,
            host=host,
            enable_exception_autocapture=True,
        )
        atexit.register(client.shutdown)
        return client
    except Exception:
        return None


_posthog = _init_posthog()
_device_id: str | None = None


def get_device_id() -> str:
    global _device_id
    if _device_id is None:
        _device_id = _get_or_create_device_id()
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


def shutdown() -> None:
    """Flush all queued PostHog events and shut down the client."""
    if _posthog is not None:
        with contextlib.suppress(Exception):
            _posthog.shutdown()
