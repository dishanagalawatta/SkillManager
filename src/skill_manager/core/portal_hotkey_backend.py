"""FreeDesktop GlobalShortcuts portal backend for global hotkeys.

Registers global shortcuts via the FreeDesktop GlobalShortcuts portal.
Pure Wayland sessions cannot inject keys through X11, so pynput cannot
register hotkeys there.  This backend spawns ``portal_hotkeys.py`` — a
long-lived dbus-python + GLib helper — as a subprocess (the GLib mainloop
it requires conflicts with PySide6's event loop), sends bind/remove
commands on stdin, and forwards the helper's ``activated`` events on
stdout as ``hotkeyPressed``.  Portal sessions die when their D-Bus
connection closes, so the helper must stay alive for the session's
lifetime.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import subprocess
import threading

from PySide6.QtCore import QObject, Signal

from skill_manager.core.keymap import qt_sequence_to_gtk_accelerator

logger = logging.getLogger(__name__)

PORTAL_HELPER_STOP_TIMEOUT = 2.0


class PortalHotkeyBackend(QObject):
    """Registers global shortcuts via the FreeDesktop GlobalShortcuts portal.

    Spawns ``portal_hotkeys.py`` as a subprocess and communicates via
    stdin/stdout JSON lines.  The portal session lives for the lifetime
    of the subprocess.
    """

    hotkeyPressed = Signal(int)  # noqa: N815 — emits hotkey ID when pressed

    def __init__(self, parent=None):
        super().__init__(parent)
        self._proc: subprocess.Popen | None = None
        self._reader_thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self._shortcut_ids: dict[int, str] = {}  # hotkey_id -> portal shortcut id
        self._started = False

    @property
    def available(self) -> bool:
        return self._started and self._proc is not None and self._proc.poll() is None

    def start(self) -> bool:
        """Locate a portal-capable Python and spawn the helper subprocess."""
        try:
            from skill_manager.utils.portal_utils import find_portal_python
        except ImportError:
            return False
        python = find_portal_python()
        if not python:
            return False

        helper = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "utils", "portal_hotkeys.py")
        )
        try:
            self._proc = subprocess.Popen(
                [python, helper],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
            )
        except OSError as e:
            logger.error("Failed to spawn portal hotkey helper: %s", e)
            self._proc = None
            return False

        self._reader_thread = threading.Thread(
            target=self._read_events, name="portal-hotkey-reader", daemon=True
        )
        self._reader_thread.start()
        self._started = True
        return True

    def register(self, hotkey_id: int, sequence: str) -> bool:
        """Bind a hotkey. Returns True if the command was accepted."""
        if not self.available:
            return False
        # Create a unique portal_id using a hash of the sequence so GNOME/KDE GlobalShortcuts
        # portal binds the new preferred_trigger instead of falling back to cached
        # PermissionStore bindings.
        seq_hash = hashlib.md5(sequence.encode("utf-8")).hexdigest()[:8]
        new_portal_id = f"sm_{hotkey_id}_{seq_hash}"

        with self._lock:
            old_portal_id = self._shortcut_ids.get(hotkey_id)
            self._shortcut_ids[hotkey_id] = new_portal_id

        if old_portal_id and old_portal_id != new_portal_id:
            self._send({"cmd": "remove", "id": old_portal_id})

        trigger = qt_sequence_to_gtk_accelerator(sequence)
        self._send(
            {
                "cmd": "bind",
                "id": new_portal_id,
                "description": f"SkillManager hotkey {hotkey_id}",
                "preferred_trigger": trigger,
            }
        )
        return True

    def unregister(self, hotkey_id: int) -> None:
        """Remove a hotkey; the helper re-binds the remaining set."""
        with self._lock:
            portal_id = self._shortcut_ids.pop(hotkey_id, None)
        if portal_id and self.available:
            self._send({"cmd": "remove", "id": portal_id})

    def stop(self) -> None:
        """Close the portal session and terminate the helper subprocess."""
        if self._proc is None:
            return
        self._send({"cmd": "quit"})
        try:
            self._proc.wait(timeout=PORTAL_HELPER_STOP_TIMEOUT)
        except subprocess.TimeoutExpired:
            self._proc.terminate()
            try:
                self._proc.wait(timeout=PORTAL_HELPER_STOP_TIMEOUT)
            except subprocess.TimeoutExpired:
                self._proc.kill()
        self._proc = None
        self._started = False

    def _send(self, command: dict) -> None:
        if self._proc is None or self._proc.stdin is None or self._proc.poll() is not None:
            return
        try:
            self._proc.stdin.write(json.dumps(command) + "\n")
            self._proc.stdin.flush()
        except (BrokenPipeError, OSError) as e:
            logger.warning("Failed to send command to portal hotkey helper: %s", e)

    def _read_events(self) -> None:
        """Read JSON events from the helper's stdout and forward activations."""
        assert self._proc is not None and self._proc.stdout is not None
        for line in self._proc.stdout:
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                logger.warning("Malformed event from portal hotkey helper: %r", line)
                continue
            self._handle_event(event)

    def _handle_event(self, event: dict) -> None:
        kind = event.get("event")
        if kind == "activated":
            portal_id = event.get("id")
            token = event.get("activation_token")
            if token:
                os.environ["XDG_ACTIVATION_TOKEN"] = str(token)
            with self._lock:
                hotkey_id = next(
                    (hid for hid, pid in self._shortcut_ids.items() if pid == portal_id),
                    None,
                )
            if hotkey_id is not None:
                logger.info("Portal hotkey activated: id=%d", hotkey_id)
                self.hotkeyPressed.emit(hotkey_id)
            else:
                logger.warning("Portal hotkey activated for unknown shortcut %r", portal_id)
        elif kind == "bound":
            logger.info("Portal shortcut bound: %s", event.get("trigger_description"))
        elif kind == "bind_failed":
            logger.warning("Portal bind failed for %s", event.get("ids"))
        elif kind == "deactivated":
            logger.info("Portal shortcut deactivated: %s", event.get("id"))
        elif kind == "error":
            logger.error("Portal hotkey helper error: %s", event.get("message"))
        elif kind == "exiting":
            logger.info("Portal hotkey helper exiting")
        elif kind == "ready":
            logger.info("Portal hotkey session ready: %s", event.get("session"))
