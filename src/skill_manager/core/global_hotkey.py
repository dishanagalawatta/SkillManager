"""Global hotkey manager using the 'pynput' package.

Provides system-wide hotkey detection that works even when the application
is minimized or not focused. This implementation uses the 'pynput' library
which hooks into the system to listen for global hotkeys without exclusive locks.
"""

import logging
import sys
import threading

from pynput import keyboard
from PySide6.QtCore import QObject, Signal, Slot

logger = logging.getLogger(__name__)


def _qt_sequence_to_pynput(sequence: str) -> str:
    """Convert a QKeySequence string to the format expected by pynput GlobalHotKeys."""
    parts = sequence.split("+")
    pynput_parts = []

    mapping = {
        "ctrl": "<ctrl>",
        "shift": "<shift>",
        "alt": "<alt>",
        "meta": "<cmd>",
        "return": "<enter>",
        "escape": "<esc>",
        "space": "<space>",
        "tab": "<tab>",
        "backspace": "<backspace>",
        "delete": "<delete>",
        "insert": "<insert>",
        "up": "<up>",
        "down": "<down>",
        "left": "<left>",
        "right": "<right>",
        "home": "<home>",
        "end": "<end>",
        "pageup": "<page_up>",
        "pagedown": "<page_down>",
    }

    for part in parts:
        p = part.lower().strip()
        if p in mapping:
            pynput_parts.append(mapping[p])
        else:
            pynput_parts.append(p)

    return "+".join(pynput_parts)


class GlobalHotkeyManager(QObject):
    """Manages system-wide hotkeys using the 'pynput' library.

    When a hotkey is pressed, the hotkeyPressed signal is emitted
    on the main thread via Qt's signal/slot mechanism.
    """

    hotkeyPressed = Signal(int)  # noqa: N815 — Emits hotkey ID when pressed

    def __init__(self, parent=None):
        super().__init__(parent)
        self._registered_hotkeys = {}  # id -> (pynput_sequence, original_sequence)
        self._listener = None
        self._lock = threading.Lock()

    def _restart_listener(self):
        """Restarts the pynput GlobalHotKeys listener with current mappings."""
        if self._listener is not None:
            self._listener.stop()
            self._listener = None

        if not self._registered_hotkeys:
            return

        mapping = {}
        for hotkey_id, (pynput_seq, _) in self._registered_hotkeys.items():
            # Use default argument binding to capture current hotkey_id
            def make_callback(hid=hotkey_id):
                return lambda: self._on_hotkey_pressed(hid)

            mapping[pynput_seq] = make_callback()

        try:
            self._listener = keyboard.GlobalHotKeys(mapping)
            self._listener.start()
        except Exception as e:
            logger.error("Failed to start GlobalHotKeys listener: %s", e)

    @Slot(int, str)
    def register(self, hotkey_id: int, sequence: str):
        """Register a global hotkey from a QKeySequence string.

        Args:
            hotkey_id: Unique identifier for this hotkey.
            sequence: Key sequence string like "Ctrl+Shift+S".
        """
        if sys.platform != "win32":
            logger.debug("Global hotkeys only supported on Windows")
            return

        if not sequence:
            return

        pynput_seq = _qt_sequence_to_pynput(sequence)

        with self._lock:
            self._registered_hotkeys[hotkey_id] = (pynput_seq, sequence)
            logger.info(
                "Registered global hotkey id=%d: %s (mapped to %s)", hotkey_id, sequence, pynput_seq
            )
            self._restart_listener()

    @Slot(int)
    def unregister(self, hotkey_id: int):
        """Unregister a global hotkey by ID."""
        if sys.platform != "win32":
            return

        with self._lock:
            if hotkey_id in self._registered_hotkeys:
                del self._registered_hotkeys[hotkey_id]
                logger.info("Unregistered global hotkey id=%d", hotkey_id)
                self._restart_listener()

    def start(self):
        """Start method retained for compatibility. Registration occurs immediately."""
        logger.info("Global hotkey manager started")

    def stop(self):
        """Unregister all hotkeys and stop listener."""
        if sys.platform != "win32":
            return

        with self._lock:
            self._registered_hotkeys.clear()
            if self._listener is not None:
                self._listener.stop()
                self._listener = None
        logger.info("Global hotkey manager stopped")

    def _on_hotkey_pressed(self, hotkey_id: int):
        """Callback executed by the pynput library when a hotkey triggers.

        This executes on a background thread. Emitting a Qt Signal from here
        safely marshals the call to the Qt main thread event loop.
        """
        logger.info("Global hotkey triggered: id=%d", hotkey_id)
        self.hotkeyPressed.emit(hotkey_id)
