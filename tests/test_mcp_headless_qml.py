"""Unit tests for the lazy headless QML engine used by ``--mcp``.

These tests never load ``Main.qml``: the loader, the QML singleton
registration, the window ``show`` helper and the image encoder are all
monkeypatched, so the suite stays fast and never needs a display.
"""

from __future__ import annotations

import base64
import io
from types import SimpleNamespace
from typing import Any

import pytest
from PIL import Image

import skill_manager.bootstrap as bootstrap
import skill_manager.mcp.bridge._capture as bridge_capture
import skill_manager.mcp.bridge._controller as bridge_controller
import skill_manager.mcp.bridge._qml_headless as qh
import skill_manager.mcp.bridge._state as bridge_state


@pytest.fixture(autouse=True)
def _clean_headless_state():
    """Keep the module-level enable/attempt state from leaking between tests."""
    qh.reset_headless_qml()
    yield
    qh.reset_headless_qml()


def _stub_loader(monkeypatch: pytest.MonkeyPatch, engine: Any) -> dict[str, Any]:
    """Patch the QML loader + singleton registration, returning the captured kwargs."""
    captured: dict[str, Any] = {}

    def _fake_load(controller, font_bridge, **kwargs):
        captured["controller"] = controller
        captured["font_bridge"] = font_bridge
        captured.update(kwargs)
        return engine

    monkeypatch.setattr(qh, "get_qml_engine", lambda: None)
    monkeypatch.setattr(qh, "_controller_or_none", lambda: SimpleNamespace())
    monkeypatch.setattr(qh, "_register_qml_singletons", lambda controller: SimpleNamespace())
    monkeypatch.setattr(
        qh, "_show_offscreen_window", lambda engine: captured.setdefault("shown", engine)
    )
    monkeypatch.setattr(bootstrap, "_load_qml_engine", _fake_load)
    return captured


# ---------------------------------------------------------------------------
# Controller registry
# ---------------------------------------------------------------------------
def test_set_app_controller_registers_and_syncs(monkeypatch: pytest.MonkeyPatch) -> None:
    """set_app_controller() shares a controller and runs the initial sync."""
    synced: list[bool] = []
    monkeypatch.setattr(bridge_controller, "_sync_controller", lambda: synced.append(True))
    bridge_controller.reset_app_controller()
    fake = SimpleNamespace(name="controller")

    try:
        bridge_controller.set_app_controller(fake)

        assert bridge_controller.get_app_controller() is fake
        assert synced == [True]
    finally:
        bridge_controller.reset_app_controller()


def test_set_app_controller_can_skip_sync(monkeypatch: pytest.MonkeyPatch) -> None:
    """sync=False registers the controller without touching the skill models."""
    synced: list[bool] = []
    monkeypatch.setattr(bridge_controller, "_sync_controller", lambda: synced.append(True))
    bridge_controller.reset_app_controller()
    fake = SimpleNamespace(name="controller")

    try:
        bridge_controller.set_app_controller(fake, sync=False)

        assert bridge_controller.get_app_controller() is fake
        assert synced == []
    finally:
        bridge_controller.reset_app_controller()


def test_set_app_controller_rejects_none() -> None:
    """Registering None is a programming error, not a silent no-op."""
    with pytest.raises(ValueError):
        bridge_controller.set_app_controller(None)  # type: ignore[arg-type]


def test_reset_app_controller_clears_cache() -> None:
    """reset_app_controller() drops the cached instance."""
    bridge_controller.reset_app_controller()
    assert bridge_controller._APP_CONTROLLER is None


def test_get_qml_engine_reads_private_attribute() -> None:
    """The engine is stored as ``_qml_engine`` by bootstrap._load_qml_engine."""
    engine = SimpleNamespace(rootObjects=lambda: [])
    assert bridge_controller.get_qml_engine(SimpleNamespace(_qml_engine=engine)) is engine


def test_get_qml_engine_accepts_legacy_names() -> None:
    """Legacy attribute names still resolve so older controllers keep working."""
    engine = SimpleNamespace(rootObjects=lambda: [])
    assert bridge_controller.get_qml_engine(SimpleNamespace(qml_engine=engine)) is engine
    assert bridge_controller.get_qml_engine(SimpleNamespace(engine=engine)) is engine


def test_get_qml_engine_ignores_unrelated_attributes() -> None:
    """Non-engine attributes are rejected (``rootObjects`` is required)."""
    assert bridge_controller.get_qml_engine(SimpleNamespace(engine="not-an-engine")) is None
    assert bridge_controller.get_qml_engine(SimpleNamespace()) is None


# ---------------------------------------------------------------------------
# ensure_qml_engine
# ---------------------------------------------------------------------------
def test_ensure_qml_engine_is_a_noop_when_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    """Without enable_headless_qml() nothing is loaded (tests/embedded default)."""
    monkeypatch.setattr(qh, "get_qml_engine", lambda: None)
    registrations: list[Any] = []
    monkeypatch.setattr(
        qh, "_register_qml_singletons", lambda controller: registrations.append(controller)
    )

    assert qh.ensure_qml_engine() is None
    assert registrations == []
    status = qh.qml_engine_status()
    assert status["enabled"] is False
    assert status["attempted"] is False


def test_ensure_qml_engine_reuses_existing_engine(monkeypatch: pytest.MonkeyPatch) -> None:
    """An engine that already exists (real GUI process) is returned untouched."""
    engine = SimpleNamespace(rootObjects=lambda: [object()])
    monkeypatch.setattr(qh, "get_qml_engine", lambda: engine)
    qh.enable_headless_qml(True)

    assert qh.ensure_qml_engine() is engine


def test_ensure_qml_engine_loads_and_shows_offscreen(monkeypatch: pytest.MonkeyPatch) -> None:
    """The lazy load uses the non-fatal bootstrap path and then shows the window."""
    root = object()
    engine = SimpleNamespace(rootObjects=lambda: [root])
    captured = _stub_loader(monkeypatch, engine)
    qh.enable_headless_qml(True)

    assert qh.ensure_qml_engine() is engine
    assert captured["event_name"] == "mcp_headless_qml_loaded"
    assert captured["exit_on_failure"] is False
    assert captured["shown"] is engine


def test_ensure_qml_engine_loads_only_once(monkeypatch: pytest.MonkeyPatch) -> None:
    """A successful load is reused by later calls."""
    loads: list[int] = []
    holder: dict[str, Any] = {}

    def _fake_load(controller, font_bridge, **kwargs):
        loads.append(1)
        holder["engine"] = SimpleNamespace(rootObjects=lambda: [object()])
        return holder["engine"]

    # The controller owns the engine after the load (as bootstrap._load_qml_engine does).
    monkeypatch.setattr(qh, "get_qml_engine", lambda: holder.get("engine"))
    monkeypatch.setattr(qh, "_controller_or_none", lambda: SimpleNamespace())
    monkeypatch.setattr(qh, "_register_qml_singletons", lambda controller: SimpleNamespace())
    monkeypatch.setattr(qh, "_show_offscreen_window", lambda engine: None)
    monkeypatch.setattr(bootstrap, "_load_qml_engine", _fake_load)
    qh.enable_headless_qml(True)

    first = qh.ensure_qml_engine()
    second = qh.ensure_qml_engine()

    assert first is not None
    assert second is first
    assert loads == [1]


def test_ensure_qml_engine_caches_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """A failed load is reported once and never retried on every tool call."""
    attempts: list[int] = []

    def _boom(controller, font_bridge, **kwargs):
        attempts.append(1)
        raise RuntimeError("kaboom")

    monkeypatch.setattr(qh, "get_qml_engine", lambda: None)
    monkeypatch.setattr(qh, "_controller_or_none", lambda: SimpleNamespace())
    monkeypatch.setattr(qh, "_register_qml_singletons", lambda controller: SimpleNamespace())
    monkeypatch.setattr(bootstrap, "_load_qml_engine", _boom)
    qh.enable_headless_qml(True)

    assert qh.ensure_qml_engine() is None
    assert qh.ensure_qml_engine() is None
    assert len(attempts) == 1

    status = qh.qml_engine_status()
    assert status["attempted"] is True
    assert "kaboom" in (status["error"] or "")


def test_ensure_qml_engine_survives_system_exit(monkeypatch: pytest.MonkeyPatch) -> None:
    """bootstrap's ``sys.exit(-1)`` path must not terminate the MCP server."""
    monkeypatch.setattr(qh, "get_qml_engine", lambda: None)
    monkeypatch.setattr(qh, "_controller_or_none", lambda: SimpleNamespace())
    monkeypatch.setattr(qh, "_register_qml_singletons", lambda controller: SimpleNamespace())

    def _exit(controller, font_bridge, **kwargs):
        raise SystemExit(-1)

    monkeypatch.setattr(bootstrap, "_load_qml_engine", _exit)
    qh.enable_headless_qml(True)

    assert qh.ensure_qml_engine() is None
    assert "SystemExit" in (qh.qml_engine_status()["error"] or "")


def test_ensure_qml_engine_reports_empty_root_objects(monkeypatch: pytest.MonkeyPatch) -> None:
    """An engine without root objects is treated as a failed load."""
    captured = _stub_loader(monkeypatch, SimpleNamespace(rootObjects=lambda: []))
    qh.enable_headless_qml(True)

    assert qh.ensure_qml_engine() is None
    assert captured.get("shown") is None
    assert qh.qml_engine_status()["error"] == "QML load produced no root objects"


def test_ensure_qml_engine_records_missing_controller(monkeypatch: pytest.MonkeyPatch) -> None:
    """No AppController means no load attempt and a clear status."""
    monkeypatch.setattr(qh, "get_qml_engine", lambda: None)
    monkeypatch.setattr(qh, "_controller_or_none", lambda: None)
    qh.enable_headless_qml(True)

    assert qh.ensure_qml_engine() is None
    assert qh.qml_engine_status()["error"] == "AppController unavailable"


def test_ensure_qml_engine_handles_singleton_registration_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A QML singleton registration failure degrades instead of raising."""
    monkeypatch.setattr(qh, "get_qml_engine", lambda: None)
    monkeypatch.setattr(qh, "_controller_or_none", lambda: SimpleNamespace())

    def _boom(controller):
        raise RuntimeError("already registered")

    monkeypatch.setattr(qh, "_register_qml_singletons", _boom)
    qh.enable_headless_qml(True)

    assert qh.ensure_qml_engine() is None
    status = qh.qml_engine_status()
    assert status["attempted"] is True
    assert "already registered" in (status["error"] or "")


# ---------------------------------------------------------------------------
# get_qml_window / capture_headless_window
# ---------------------------------------------------------------------------
def test_get_qml_window_without_engine(monkeypatch: pytest.MonkeyPatch) -> None:
    """No engine means no window."""
    monkeypatch.setattr(qh, "ensure_qml_engine", lambda: None)

    assert qh.get_qml_window() is None


def test_get_qml_window_ignores_non_window_roots(monkeypatch: pytest.MonkeyPatch) -> None:
    """Root objects that are not QQuickWindows are skipped."""
    monkeypatch.setattr(
        qh, "ensure_qml_engine", lambda: SimpleNamespace(rootObjects=lambda: ["nope"])
    )

    assert qh.get_qml_window() is None


def test_capture_headless_window_without_window(monkeypatch: pytest.MonkeyPatch) -> None:
    """Without a QML window the capture degrades to ``(None, 0, 0)``."""
    monkeypatch.setattr(qh, "get_qml_window", lambda: None)

    assert qh.capture_headless_window() == (None, 0, 0)


class _FakeWindow:
    """Minimal QQuickWindow stand-in for the offscreen capture path."""

    def __init__(self, width: int = 800, height: int = 600, image: Any = None) -> None:
        self._width = width
        self._height = height
        self._image = image
        self.set_calls: list[tuple[str, int]] = []

    def width(self) -> int:
        return self._width

    def height(self) -> int:
        return self._height

    def setWidth(self, value: int) -> None:  # noqa: N802 - Qt spelling
        self._width = int(value)
        self.set_calls.append(("w", int(value)))

    def setHeight(self, value: int) -> None:  # noqa: N802 - Qt spelling
        self._height = int(value)
        self.set_calls.append(("h", int(value)))

    def grabWindow(self):  # noqa: N802 - Qt spelling
        if isinstance(self._image, BaseException):
            raise self._image
        return self._image


def test_capture_headless_window_encodes_image(monkeypatch: pytest.MonkeyPatch) -> None:
    """A successful grab returns the encoded PNG plus the image dimensions."""
    image = SimpleNamespace(isNull=lambda: False, width=lambda: 800, height=lambda: 600)
    window = _FakeWindow(image=image)
    monkeypatch.setattr(qh, "get_qml_window", lambda: window)
    monkeypatch.setattr(qh, "_image_to_base64_png", lambda img: "BASE64")

    assert qh.capture_headless_window() == ("BASE64", 800, 600)


def test_capture_headless_window_null_image(monkeypatch: pytest.MonkeyPatch) -> None:
    """A null grab (unexposed window) degrades to ``(None, 0, 0)``."""
    image = SimpleNamespace(isNull=lambda: True, width=lambda: 800, height=lambda: 600)
    monkeypatch.setattr(qh, "get_qml_window", lambda: _FakeWindow(image=image))

    assert qh.capture_headless_window() == (None, 0, 0)


def test_capture_headless_window_resizes_and_restores(monkeypatch: pytest.MonkeyPatch) -> None:
    """Requested resize is applied before the grab and restored afterwards."""
    image = SimpleNamespace(isNull=lambda: False, width=lambda: 900, height=lambda: 500)
    window = _FakeWindow(image=image)
    monkeypatch.setattr(qh, "get_qml_window", lambda: window)
    monkeypatch.setattr(qh, "_image_to_base64_png", lambda img: "BASE64")

    assert qh.capture_headless_window(900, 500) == ("BASE64", 900, 500)
    assert window.set_calls == [("w", 900), ("h", 500), ("w", 800), ("h", 600)]


def test_capture_headless_window_restores_after_grab_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A grab exception still restores the original window size."""
    window = _FakeWindow(image=RuntimeError("no render"))
    monkeypatch.setattr(qh, "get_qml_window", lambda: window)

    assert qh.capture_headless_window(900, 500) == (None, 0, 0)
    assert window.set_calls == [("w", 900), ("h", 500), ("w", 800), ("h", 600)]


def test_image_to_base64_png_round_trips() -> None:
    """The encoder produces a PNG that PIL can decode."""
    from PySide6.QtGui import QImage

    image = QImage(4, 3, QImage.Format_RGB32)
    image.fill(0xFF336699)

    encoded = qh._image_to_base64_png(image)

    assert encoded is not None
    raw = base64.b64decode(encoded)
    with Image.open(io.BytesIO(raw)) as decoded:
        assert decoded.size == (4, 3)


# ---------------------------------------------------------------------------
# capture_app_window_info — provenance + headless fallback
# ---------------------------------------------------------------------------
def _no_ipc(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(bridge_capture, "_find_skill_manager_window", lambda: None)
    monkeypatch.setattr(
        bridge_capture, "send_capture_command", lambda **kwargs: {"ok": False, "error": "no GUI"}
    )


def _set_native_capture(
    monkeypatch: pytest.MonkeyPatch, result: tuple[str | None, int, int]
) -> None:
    """Force the outcome of the platform-native capture on whichever OS runs.

    ``capture_app_window_info`` dispatches on ``sys.platform``, so patching only
    ``_fallback_capture_linux`` silently stopped working on the Windows CI
    runner (it calls ``_fallback_capture_win32``).
    """
    monkeypatch.setattr(bridge_capture, "_fallback_capture_linux", lambda *a, **kw: result)
    monkeypatch.setattr(bridge_capture, "_fallback_capture_win32", lambda *a, **kw: result)


def test_capture_info_reports_live_gui(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    """An IPC capture is labelled ``live-gui``."""
    image_path = tmp_path / "shot.png"
    Image.new("RGB", (12, 7), "blue").save(image_path)
    _no_ipc(monkeypatch)
    # On Windows the IPC strategy is skipped unless a window handle exists, so
    # supply one: provenance must not depend on which OS runs the suite.
    monkeypatch.setattr(bridge_capture, "_find_skill_manager_window", lambda: 4242)
    monkeypatch.setattr(
        bridge_capture,
        "send_capture_command",
        lambda **kwargs: {"ok": True, "capture_path": str(image_path)},
    )

    info = bridge_capture.capture_app_window_info()

    assert info["source"] == "live-gui"
    assert (info["width"], info["height"]) == (12, 7)
    assert info["image_b64"]


def test_capture_info_reports_native(monkeypatch: pytest.MonkeyPatch) -> None:
    """A platform-native capture is labelled ``native``."""
    _no_ipc(monkeypatch)
    _set_native_capture(monkeypatch, ("NATIVE", 20, 10))
    monkeypatch.setattr(qh, "headless_qml_enabled", lambda: False)

    info = bridge_capture.capture_app_window_info()

    assert info["source"] == "native"
    assert (info["width"], info["height"]) == (20, 10)


def test_capture_info_falls_back_to_headless_qml(monkeypatch: pytest.MonkeyPatch) -> None:
    """With no GUI, an enabled headless engine provides the render."""
    _no_ipc(monkeypatch)
    _set_native_capture(monkeypatch, (None, 0, 0))
    monkeypatch.setattr(qh, "headless_qml_enabled", lambda: True)
    monkeypatch.setattr(qh, "capture_headless_window", lambda *a, **kw: ("HEADLESS", 800, 600))

    info = bridge_capture.capture_app_window_info(900, 500)

    assert info["source"] == "headless-qml"
    assert (info["image_b64"], info["width"], info["height"]) == ("HEADLESS", 800, 600)


def test_capture_info_skips_headless_when_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    """Headless rendering is opt-in, so the bridge stays inert outside --mcp."""
    _no_ipc(monkeypatch)
    _set_native_capture(monkeypatch, (None, 0, 0))
    called: list[int] = []
    monkeypatch.setattr(qh, "headless_qml_enabled", lambda: False)
    monkeypatch.setattr(qh, "capture_headless_window", lambda *a, **kw: called.append(1))

    info = bridge_capture.capture_app_window_info()

    assert info["source"] is None
    assert info["error"] == "capture_failed"
    assert called == []


def test_capture_info_windows_requires_a_window_handle_for_ipc(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """On Windows the IPC strategy is skipped unless a window handle exists.

    Pinned deliberately: CI runs these tests on ``windows-latest``, where the
    guard below decides which strategies are reachable at all. Emulating the
    platform inside the module keeps the contract tested on Linux too.
    """
    monkeypatch.setattr(bridge_capture, "sys", SimpleNamespace(platform="win32"))
    monkeypatch.setattr(bridge_capture, "_find_skill_manager_window", lambda: None)
    _set_native_capture(monkeypatch, (None, 0, 0))
    monkeypatch.setattr(qh, "headless_qml_enabled", lambda: False)
    ipc_calls: list[int] = []
    monkeypatch.setattr(
        bridge_capture,
        "send_capture_command",
        lambda **kwargs: ipc_calls.append(1) or {"ok": False},
    )

    info = bridge_capture.capture_app_window_info()

    assert ipc_calls == [], "Windows must not send an IPC capture command without a window"
    assert info["source"] is None
    assert info["error"] == "capture_failed"


def test_capture_app_window_still_returns_tuple(monkeypatch: pytest.MonkeyPatch) -> None:
    """The legacy tuple API is preserved for existing callers."""
    monkeypatch.setattr(
        bridge_capture,
        "capture_app_window_info",
        lambda **kwargs: {"image_b64": "B64", "width": 3, "height": 4, "source": "native"},
    )

    assert bridge_capture.capture_app_window(1, 1) == ("B64", 3, 4)


# ---------------------------------------------------------------------------
# Health reporting
# ---------------------------------------------------------------------------
def test_get_health_reports_qml_status(monkeypatch: pytest.MonkeyPatch) -> None:
    """sm_get_health surfaces whether the QML engine is available."""
    monkeypatch.setattr(bridge_state, "_controller_or_none", lambda: SimpleNamespace())
    monkeypatch.setattr(
        qh,
        "qml_engine_status",
        lambda: {"enabled": True, "loaded": False, "error": None},
    )

    health = bridge_state.get_health()

    assert health["qml"] == {"enabled": True, "loaded": False, "error": None}


def test_get_health_qml_empty_when_controller_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    """The degraded health envelope still carries an empty ``qml`` dict."""
    monkeypatch.setattr(bridge_state, "_controller_or_none", lambda: None)

    health = bridge_state.get_health()

    assert health["qml"] == {}
