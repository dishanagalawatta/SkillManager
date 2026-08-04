"""File-based IPC channel for cross-process GUI navigation.

Extracted from ``app.py`` during Phase 1 of the codebase refactor; re-exported
from ``skill_manager.app`` so ``from skill_manager.app import CommandChannel``
keeps working. The class is self-contained — the ``app_controller`` argument is
duck-typed (``app.ui.currentView``, ``app.debugOverlayEnabled``,
``app._qml_engine``).
"""

import contextlib
import json
import logging
import time
from pathlib import Path

from PySide6.QtCore import QCoreApplication, QEvent, QFileSystemWatcher, QObject, QTimer
from PySide6.QtGui import QImage
from PySide6.QtQuick import QQuickWindow

logger = logging.getLogger(__name__)


def _normalize_capture_image(image: QImage) -> QImage:
    """Return a copy of *image* in a canonical 8-bit format for PNG export.

    ``QQuickWindow::grabWindow()`` can return an image whose native pixel
    format (e.g. 30-bit BGR on Wayland) or device-pixel-ratio metadata makes
    Qt's PNG writer emit a corrupt IDAT stream. Converting to plain
    RGBA8888 at DPR 1.0 yields a PNG that PIL and other decoders can read.
    """
    normalized = image.convertToFormat(QImage.Format_RGBA8888)
    normalized.setDevicePixelRatio(1.0)
    return normalized


class CommandChannel(QObject):
    """File-based IPC channel for cross-process GUI navigation.

    The MCP bridge (headless, offscreen) cannot see or move the real GUI
    window, so it writes a JSON command into ``data/mcp/commands/``.
    This channel polls the directory every 200ms via ``QTimer`` (primary,
    reliable on all platforms) and also uses ``QFileSystemWatcher`` (secondary
    optimisation for near-instant notification). On a command it switches
    the live view on the Qt thread and writes an acknowledgement into
    ``data/mcp/acks/<id>.json``. Processed command files are deleted
    immediately to avoid re-processing; stale ack files are cleaned up.
    Setup is best-effort: if directories cannot be created it degrades to
    a no-op rather than crashing ``AppController``.
    """

    VALID_VIEWS = ("QuickCopy", "Library", "Updates", "Settings")
    _POLL_INTERVAL_MS = 200
    _STALE_AGE = 30.0  # seconds — ack files older than this are removed on poll

    def __init__(self, app_controller):
        super().__init__()
        self.app = app_controller
        self._watcher = None
        self._timer = None
        self._commands_dir = None
        self._acks_dir = None
        self._setup()

    def _setup(self) -> None:
        try:
            base = Path(__file__).resolve().parents[3] / "data" / "mcp"
            commands_dir = base / "commands"
            acks_dir = base / "acks"
            commands_dir.mkdir(parents=True, exist_ok=True)
            acks_dir.mkdir(parents=True, exist_ok=True)
            self._commands_dir = commands_dir
            self._acks_dir = acks_dir

            # Primary: QTimer-based polling (reliable on Windows, works everywhere).
            self._timer = QTimer(self)
            self._timer.timeout.connect(self._poll_commands)
            self._timer.start(self._POLL_INTERVAL_MS)

            # Secondary: QFileSystemWatcher (near-instant when it works).
            try:
                self._watcher = QFileSystemWatcher()
                self._watcher.directoryChanged.connect(self._poll_commands)
                self._watcher.addPath(str(commands_dir))
            except Exception:  # noqa: BLE001 — degraded: poll-only
                self._watcher = None

        except Exception as exc:  # noqa: BLE001 — degrade, never crash
            logger.warning("CommandChannel disabled (headless/CI?): %s", exc)
            self._commands_dir = None

    def stop(self) -> None:
        """Release watcher and timer. Idempotent; safe to call multiple times.

        Required so controllers created in tests/MCP bridges do not leak
        inotify instances on the host.
        """
        watcher = getattr(self, "_watcher", None)
        if watcher is not None:
            with contextlib.suppress(TypeError):
                watcher.directoryChanged.disconnect(self._poll_commands)
            watcher.deleteLater()
            self._watcher = None
        timer = getattr(self, "_timer", None)
        if timer is not None:
            timer.stop()
            timer.deleteLater()
            self._timer = None
        # Flush deferred deletes now so the inotify fd is released even when
        # no event loop runs afterwards (e.g. pytest workers, probe scripts).
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)

    def _poll_commands(self) -> None:
        """Check for new command files and process every pending one.

        Processes command files in FIFO order (oldest first). Each is
        deleted immediately after processing to prevent re-processing.
        Stale ack files are pruned on each poll cycle.
        """
        if self._commands_dir is None:
            return

        self._prune_stale_acks()

        try:
            files = sorted(
                self._commands_dir.glob("*.json"),
                key=lambda p: p.stat().st_mtime,
            )
        except Exception:  # noqa: BLE001
            return
        if not files:
            return

        for cmd_file in files:
            try:
                data = json.loads(cmd_file.read_text(encoding="utf-8"))
            except Exception:  # noqa: BLE001 — invalid JSON, skip
                cmd_file.unlink(missing_ok=True)
                continue
            self._handle_command(data)
            cmd_file.unlink(missing_ok=True)

    def _prune_stale_acks(self) -> None:
        """Remove ack files older than ``_STALE_AGE`` seconds."""
        if self._acks_dir is None:
            return
        now = time.monotonic()
        try:
            for p in self._acks_dir.glob("*.json"):
                try:
                    age = now - p.stat().st_mtime
                    if age > self._STALE_AGE:
                        p.unlink()
                except OSError:
                    pass
        except Exception:  # noqa: BLE001
            pass

    def _handle_command(self, data: dict) -> None:
        cmd_id = data.get("id")
        action = data.get("action")

        if action == "navigate":
            view = data.get("view")
            if view not in self.VALID_VIEWS:
                self._write_ack(cmd_id, ok=False, error=f"invalid view: {view!r}")
                return
            self._apply_view(cmd_id, view)
        elif action == "set_debug_overlay":
            enabled = bool(data.get("enabled", True))
            self.app.debugOverlayEnabled = enabled
            self._write_ack(cmd_id, ok=True)
        elif action == "capture_screenshot":
            self._capture_screenshot(cmd_id)
        else:
            self._write_ack(cmd_id, ok=False, error=f"unknown action: {action!r}")

    def _capture_screenshot(self, cmd_id: str | None) -> None:
        """Grab the QML window content via the render engine (works minimised)."""
        if not cmd_id:
            return
        try:
            engine = getattr(self.app, "_qml_engine", None)
            if engine is None:
                self._write_ack(cmd_id, ok=False, error="no QML engine")
                return
            roots = engine.rootObjects()
            if not roots:
                self._write_ack(cmd_id, ok=False, error="no QML root objects")
                return
            window = roots[0]
            if not isinstance(window, QQuickWindow):
                self._write_ack(cmd_id, ok=False, error="root object is not a QQuickWindow")
                return

            image = window.grabWindow()
            if image.isNull():
                self._write_ack(cmd_id, ok=False, error="grabWindow returned null image")
                return

            if self._commands_dir is None:
                self._write_ack(cmd_id, ok=False, error="commands dir not available")
                return
            captures_dir = self._commands_dir.parent / "captures"
            captures_dir.mkdir(parents=True, exist_ok=True)
            out_path = captures_dir / f"{cmd_id}.png"
            if not _normalize_capture_image(image).save(str(out_path)):
                self._write_ack(cmd_id, ok=False, error="failed to save PNG")
                return

            self._write_ack(cmd_id, ok=True, capture_path=str(out_path.resolve()))
        except Exception as exc:  # noqa: BLE001
            self._write_ack(cmd_id, ok=False, error=str(exc))

    def _apply_view(self, cmd_id, view) -> None:
        try:
            self.app.ui.currentView = view
        except Exception as exc:  # noqa: BLE001
            self._write_ack(cmd_id, ok=False, error=str(exc))
            return
        self._write_ack(cmd_id, ok=True, view=view)

    def _write_ack(self, cmd_id, ok, error=None, view=None, **extra) -> None:
        if not cmd_id or self._acks_dir is None:
            return
        ack: dict[str, object] = {"ok": ok}
        if view is not None:
            ack["view"] = view
        if error is not None:
            ack["error"] = error
        ack.update(extra)
        with contextlib.suppress(Exception):
            (self._acks_dir / f"{cmd_id}.json").write_text(json.dumps(ack), encoding="utf-8")
