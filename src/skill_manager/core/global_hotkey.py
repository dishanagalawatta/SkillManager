"""Global hotkey manager using pynput (lazy-loaded).

Architecture:
- Pure key-sequence conversion lives in ``skill_manager.core.keymap``
- pynput is lazy-imported only when ``register()`` is called
- Graceful degradation: if pynput is unavailable, ``register()`` returns
  ``False`` and the app continues to function (screenshot hotkey is the
  only feature using this)

Per pynput's official documentation, the recommended pattern for
hotkey sets that can change at runtime is ``HotKey`` + ``Listener``
(rather than ``GlobalHotKeys``, which is optimized for a fixed mapping).
"""

from __future__ import annotations

import contextlib
import logging
import threading
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, Signal, Slot

from skill_manager.core.keymap import qt_sequence_to_pynput_keys

if TYPE_CHECKING:
    from pynput import keyboard  # noqa: F401

logger = logging.getLogger(__name__)

_LISTENER_JOIN_TIMEOUT = 2.0


class GlobalHotkeyManager(QObject):
    """Manages system-wide hotkeys via pynput's HotKey + Listener pattern.

    When a hotkey is pressed, the ``hotkeyPressed`` signal is emitted
    on the main thread via Qt's signal/slot mechanism.

    The underlying pynput ``Listener`` thread is tracked explicitly so
    that ``stop()`` can ``join()`` it with a timeout, preventing
    access-violation crashes when Python's GC runs finalizers before
    the listener thread has exited.
    """

    hotkeyPressed = Signal(int)  # noqa: N815 — emits hotkey ID when pressed

    def __init__(self, parent=None):
        super().__init__(parent)
        self._hotkeys: dict[int, tuple[str, str]] = {}  # id -> (pynput_seq, original)
        self._listener = None
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self._stop_lock = threading.Lock()
        self._pynput_available: bool | None = None  # None = unchecked

    def __del__(self) -> None:
        with contextlib.suppress(Exception):
            self.stop()

    def _ensure_pynput(self) -> bool:
        """Lazy-import pynput. Returns True if usable, False if not."""
        if self._pynput_available is not None:
            return self._pynput_available
        try:
            from pynput import keyboard  # noqa: F401

            self._pynput_available = True
        except (ImportError, OSError) as e:
            logger.warning("pynput unavailable: %s. Global hotkeys will not function.", e)
            self._pynput_available = False
        return self._pynput_available

    def _restart_listener(self) -> None:
        """Start or restart the pynput Listener with current hotkey mappings."""
        if not self._ensure_pynput():
            return
        from pynput import keyboard

        self._stop_active_listener()

        if not self._hotkeys:
            return

        # Per pynput docs: build one HotKey per mapping, share a single Listener
        hotkey_objs = [
            keyboard.HotKey(
                keyboard.HotKey.parse(pynput_seq),
                _make_callback(self, hid),
            )
            for hid, (pynput_seq, _) in self._hotkeys.items()
        ]

        def on_press(key):
            listener = self._listener
            if listener is None:
                return
            canonical = listener.canonical(key)
            for hk in hotkey_objs:
                hk.press(canonical)

        def on_release(key):
            listener = self._listener
            if listener is None:
                return
            canonical = listener.canonical(key)
            for hk in hotkey_objs:
                hk.release(canonical)

        try:
            self._listener = keyboard.Listener(on_press=on_press, on_release=on_release)
            self._thread = getattr(self._listener, "_thread", None)
            self._listener.start()
        except OSError as e:
            logger.error("Failed to start pynput listener: %s", e)
            self._listener = None
            self._thread = None

    def _stop_active_listener(self) -> None:
        """Stop the current listener and join its thread with a timeout.

        Uses ``_stop_lock`` so concurrent calls are serialised.  If the
        join times out the thread is left as a daemon and will be killed
        when the interpreter exits — no crash, no hang.
        """
        with self._stop_lock:
            listener = self._listener
            thread = self._thread
            self._listener = None
            self._thread = None

        if listener is None:
            return

        try:
            listener.stop()
        except Exception:  # noqa: BLE001 — defensive
            logger.debug("Error stopping pynput listener", exc_info=True)

        if thread is not None and thread.is_alive():
            thread.join(timeout=_LISTENER_JOIN_TIMEOUT)
            if thread.is_alive():
                logger.warning(
                    "pynput listener thread did not exit within %ss; leaving as daemon",
                    _LISTENER_JOIN_TIMEOUT,
                )

    @Slot(int, str)
    def register(self, hotkey_id: int, sequence: str) -> bool:
        """Register a global hotkey from a QKeySequence string.

        Args:
            hotkey_id: Unique identifier for this hotkey.
            sequence: Key sequence string like "Ctrl+Shift+S".

        Returns:
            True if registered, False if pynput is unavailable or
            sequence is empty.
        """
        if not sequence:
            return False
        if not self._ensure_pynput():
            return False

        pynput_seq = qt_sequence_to_pynput_keys(sequence)

        with self._lock:
            self._hotkeys[hotkey_id] = (pynput_seq, sequence)
            logger.info(
                "Registered global hotkey id=%d: %s (mapped to %s)",
                hotkey_id,
                sequence,
                pynput_seq,
            )
            self._restart_listener()
        return True

    @Slot(int)
    def unregister(self, hotkey_id: int) -> None:
        """Unregister a global hotkey by ID."""
        with self._lock:
            if hotkey_id in self._hotkeys:
                del self._hotkeys[hotkey_id]
                logger.info("Unregistered global hotkey id=%d", hotkey_id)
                self._restart_listener()

    def start(self) -> None:
        """Start method retained for compatibility. Registration occurs immediately."""
        logger.info("Global hotkey manager started")

    def stop(self) -> None:
        """Unregister all hotkeys and stop listener."""
        with self._lock:
            self._hotkeys.clear()
        self._stop_active_listener()
        logger.info("Global hotkey manager stopped")

    def _on_hotkey_pressed(self, hotkey_id: int) -> None:
        """Callback executed by the pynput library when a hotkey triggers.

        This executes on a background thread. Emitting a Qt Signal from here
        safely marshals the call to the Qt main thread event loop.
        """
        logger.info("Global hotkey triggered: id=%d", hotkey_id)
        self.hotkeyPressed.emit(hotkey_id)


def _make_callback(manager: GlobalHotkeyManager, hotkey_id: int):
    """Build a closure that calls ``_on_hotkey_pressed`` on the manager.

    Pynput invokes the registered callable with no arguments; we use
    a closure factory to bind the hotkey_id at registration time.
    """

    def callback():
        manager._on_hotkey_pressed(hotkey_id)

    return callback
