"""QML render frame-timing profiling for the MCP bridge.

Captures QML render frame durations over a sampling window by connecting to
the QQuickWindow's beforeRendering/afterRendering signals, then reports FPS,
avg/p95/max frame ms, and dropped frames. Falls back gracefully when the QML
engine or window is not available (headless MCP mode).
"""

from __future__ import annotations

import time
from typing import Any

from ._controller import _controller_or_none
from ._qml_headless import ensure_qml_engine
from ._telemetry import _log_call

# Frame budget threshold (ms) above which a frame is considered "dropped"
# at 60 Hz (16.67 ms per frame).
_DROP_THRESHOLD_MS = 16.67

# Interval used to drive forced redraws when ``force_render`` is set (60 Hz).
_FORCE_INTERVAL_MS = 16


def get_frame_timing(duration_s: float = 2.0, force_render: bool = False) -> dict[str, Any]:
    """Capture QML render frame timings over *duration_s* seconds.

    Connects a temporary QObject to the QML window's
    ``beforeRendering`` / ``afterRendering`` signals to measure per-frame
    render duration. Samples for *duration_s* seconds, then disconnects.

    An idle window renders nothing, which is why the headless (offscreen) window
    otherwise reports zero frames. Pass ``force_render=True`` to drive a 60 Hz
    ``update()`` cadence so real per-frame render costs can be measured; the
    reported ``fps`` is then cadence-bound while ``avg_frame_ms`` /
    ``p95_frame_ms`` remain the meaningful signal.

    Falls back to a perf_counter-based approximation when the QML engine,
    window or render loop is unavailable.

    Returns a dict with: ok, duration_s, mode, frame_count, fps, avg_frame_ms,
    p95_frame_ms, max_frame_ms, dropped_frames, samples, error.
    """
    _log_call("get_frame_timing")

    try:
        duration_s = float(duration_s)
        if duration_s < 0.5 or duration_s > 30.0:
            return {
                "ok": False,
                "duration_s": duration_s,
                "mode": "invalid",
                "frame_count": 0,
                "fps": 0.0,
                "avg_frame_ms": 0.0,
                "p95_frame_ms": 0.0,
                "max_frame_ms": 0.0,
                "dropped_frames": 0,
                "samples": [],
                "error": "duration_s must be between 0.5 and 30 seconds",
            }
    except (TypeError, ValueError) as exc:
        return {
            "ok": False,
            "duration_s": 0.0,
            "mode": "invalid",
            "frame_count": 0,
            "fps": 0.0,
            "avg_frame_ms": 0.0,
            "p95_frame_ms": 0.0,
            "max_frame_ms": 0.0,
            "dropped_frames": 0,
            "samples": [],
            "error": f"invalid duration_s: {exc}",
        }

    controller = _controller_or_none()
    if controller is None:
        return _fallback_frame_timing(duration_s, "AppController unavailable")

    qml_engine = ensure_qml_engine()
    if qml_engine is None:
        return _fallback_frame_timing(duration_s, "QML engine not available")

    roots = qml_engine.rootObjects()
    if not roots:
        return _fallback_frame_timing(duration_s, "no QML root objects")

    window = roots[0]
    try:
        from PySide6.QtCore import QObject, QTimer  # type: ignore[import-not-found]
        from PySide6.QtQuick import QQuickWindow  # type: ignore[import-not-found]
    except Exception as exc:  # noqa: BLE001
        return _fallback_frame_timing(duration_s, f"PySide6 import failed: {exc}")

    if not isinstance(window, QQuickWindow):
        return _fallback_frame_timing(duration_s, "root object is not a QQuickWindow")

    # A window that is neither exposed nor visible has no live render loop (the
    # headless/offscreen MCP window, or a fully hidden GUI). Sampling would
    # block for duration_s and report 0 frames without explaining why, so
    # degrade immediately with an actionable reason instead.
    if not _window_has_live_render_loop(window):
        return _fallback_frame_timing(
            duration_s,
            "no live render loop: the QML window is not exposed "
            "(headless/offscreen, or hidden). Frame timing needs the visible GUI.",
        )

    samples: list[dict[str, Any]] = []
    state = {"start": None, "frame_index": 0, "collecting": True}

    class _FrameProbe(QObject):
        """Temporary QObject that connects to rendering signals."""

        def __init__(self, win: QQuickWindow) -> None:
            super().__init__()
            self._win = win
            self._before = time.perf_counter()
            win.beforeRendering.connect(self._on_before)
            win.afterRendering.connect(self._on_after)

        def _on_before(self) -> None:
            if not state["collecting"]:
                return
            state["start"] = time.perf_counter()

        def _on_after(self) -> None:
            if not state["collecting"] or state["start"] is None:
                return
            elapsed_ms = (time.perf_counter() - state["start"]) * 1000.0
            samples.append(
                {
                    "frame_index": state["frame_index"],
                    "duration_ms": round(elapsed_ms, 4),
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                }
            )
            state["frame_index"] += 1
            state["start"] = None

        def disconnect(self) -> None:
            try:
                self._win.beforeRendering.disconnect(self._on_before)
                self._win.afterRendering.disconnect(self._on_after)
            except Exception:  # noqa: BLE001
                pass
            self.deleteLater()

    probe = _FrameProbe(window)

    # Optionally drive a 60 Hz redraw cadence: an idle window renders nothing,
    # so without this a settled UI always reports zero frames.
    force_timer = None
    if force_render:
        try:
            force_timer = QTimer()
            force_timer.setInterval(_FORCE_INTERVAL_MS)
            force_timer.timeout.connect(window.update)
            force_timer.start()
        except Exception:  # noqa: BLE001
            force_timer = None

    # Sample for duration_s seconds using a timer + event loop.
    try:
        from PySide6.QtCore import QEventLoop  # type: ignore[import-not-found]

        loop = QEventLoop()
        timer = QTimer()
        timer.setSingleShot(True)
        timer.timeout.connect(loop.quit)
        timer.start(int(duration_s * 1000))

        # Process events until the timer fires (collecting samples meanwhile).
        loop.exec()

        state["collecting"] = False
    except Exception:  # noqa: BLE001
        # If we can't run an event loop, fall back to a perf_counter spin.
        deadline = time.perf_counter() + duration_s
        while time.perf_counter() < deadline:
            pass
        state["collecting"] = False

    if force_timer is not None:
        try:
            force_timer.stop()
            force_timer.deleteLater()
        except Exception:  # noqa: BLE001
            pass

    probe.disconnect()

    # Compute statistics.
    frame_count = len(samples)
    durations = [s["duration_ms"] for s in samples]
    mode = "forced_60hz" if force_render else "natural"
    if frame_count == 0:
        return {
            "ok": True,
            "duration_s": duration_s,
            "mode": mode,
            "frame_count": 0,
            "fps": 0.0,
            "avg_frame_ms": 0.0,
            "p95_frame_ms": 0.0,
            "max_frame_ms": 0.0,
            "dropped_frames": 0,
            "samples": [],
            "error": (
                "no frames observed in the sampling window: the window rendered "
                "nothing (idle UI). Re-run with force_render=true to measure a "
                "60 Hz forced redraw cadence."
            ),
        }

    avg_ms = sum(durations) / frame_count
    max_ms = max(durations)
    sorted_durations = sorted(durations)
    p95_index = max(0, int(round(0.95 * frame_count)) - 1)
    p95_ms = sorted_durations[p95_index]
    dropped = sum(1 for d in durations if d > _DROP_THRESHOLD_MS)
    fps = frame_count / duration_s if duration_s > 0 else 0.0

    return {
        "ok": True,
        "duration_s": round(duration_s, 4),
        "mode": mode,
        "frame_count": frame_count,
        "fps": round(fps, 2),
        "avg_frame_ms": round(avg_ms, 4),
        "p95_frame_ms": round(p95_ms, 4),
        "max_frame_ms": round(max_ms, 4),
        "dropped_frames": dropped,
        "samples": samples,
        "error": None,
    }


def _window_has_live_render_loop(window: Any) -> bool:
    """Return whether *window* is rendering frames (exposed and not hidden).

    ``QQuickWindow.isExposed()`` is the authoritative signal: it is ``False``
    for offscreen/headless windows and for windows that are not on screen, in
    which case no ``beforeRendering`` ticks occur.
    """
    try:
        exposed = window.isExposed()
    except Exception:  # noqa: BLE001
        exposed = None
    if exposed is False:
        return False
    if exposed is None:
        try:
            return bool(window.isVisible())
        except Exception:  # noqa: BLE001
            return False
    return True


def _fallback_frame_timing(duration_s: float, reason: str) -> dict[str, Any]:
    """Fallback when QML engine/window/render loop is unavailable.

    Returns a degraded result with ok=True but zero frames, explaining the
    reason so callers understand headless mode limitations.
    """
    return {
        "ok": True,
        "duration_s": round(duration_s, 4),
        "mode": "unavailable",
        "frame_count": 0,
        "fps": 0.0,
        "avg_frame_ms": 0.0,
        "p95_frame_ms": 0.0,
        "max_frame_ms": 0.0,
        "dropped_frames": 0,
        "samples": [],
        "error": reason,
    }


__all__ = ["get_frame_timing"]
