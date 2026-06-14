"""Global hotkey manager using Win32 RegisterHotKey API.

Provides system-wide hotkey detection that works even when the application
is minimized or not focused. This is the same approach used by popular
screenshot tools like Greenshot and ShareX.
"""

import ctypes
import logging
import sys
import threading
from ctypes import wintypes

from PySide6.QtCore import QObject, Qt, Signal, Slot
from PySide6.QtGui import QKeySequence

logger = logging.getLogger(__name__)

# Win32 constants
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
MOD_NOREPEAT = 0x4000
WM_HOTKEY = 0x0312

# Qt key code ranges
QT_KEY_A = 0x41
QT_KEY_Z = 0x5A
QT_KEY_0 = 0x30
QT_KEY_9 = 0x39
# Qt Key.Key_F1 = 0x1000030, Key.Key_F24 = 0x1000047
QT_KEY_F1 = 0x1000030
QT_KEY_F24 = 0x1000047

# Virtual key codes for F keys (Win32)
VK_F1 = 0x70


def _qt_key_to_win32_vkey(key: int) -> int | None:
    """Convert a Qt key code to a Win32 virtual key code."""
    if QT_KEY_A <= key <= QT_KEY_Z:
        return key
    if QT_KEY_0 <= key <= QT_KEY_9:
        return key
    if QT_KEY_F1 <= key <= QT_KEY_F24:
        return VK_F1 + (key - QT_KEY_F1)
    # Common special keys (Qt.Key enum values)
    special_map = {
        Qt.Key.Key_Space: 0x20,
        Qt.Key.Key_Tab: 0x09,
        Qt.Key.Key_Return: 0x0D,
        Qt.Key.Key_Escape: 0x1B,
        Qt.Key.Key_Delete: 0x2E,
        Qt.Key.Key_Insert: 0x2D,
        Qt.Key.Key_Home: 0x24,
        Qt.Key.Key_End: 0x23,
        Qt.Key.Key_PageUp: 0x21,
        Qt.Key.Key_PageDown: 0x22,
        Qt.Key.Key_Left: 0x25,
        Qt.Key.Key_Up: 0x26,
        Qt.Key.Key_Right: 0x27,
        Qt.Key.Key_Down: 0x28,
        Qt.Key.Key_Print: 0x2C,
        Qt.Key.Key_Pause: 0x13,
        Qt.Key.Key_ScrollLock: 0x91,
        Qt.Key.Key_CapsLock: 0x14,
        Qt.Key.Key_NumLock: 0x90,
    }
    return special_map.get(key)


def _qt_modifiers_to_win32(modifiers) -> int:
    """Convert Qt keyboard modifiers to Win32 modifier flags."""
    result = 0
    if modifiers & Qt.KeyboardModifier.ControlModifier:
        result |= MOD_CONTROL
    if modifiers & Qt.KeyboardModifier.AltModifier:
        result |= MOD_ALT
    if modifiers & Qt.KeyboardModifier.ShiftModifier:
        result |= MOD_SHIFT
    if modifiers & Qt.KeyboardModifier.MetaModifier:
        result |= MOD_WIN
    return result


def parse_key_sequence(sequence: str) -> tuple[int, int] | None:
    """Parse a QKeySequence string into Win32 modifiers and virtual key code.

    Returns (modifiers, vkey) tuple or None if parsing fails.
    """
    ks = QKeySequence(sequence)
    if ks.isEmpty():
        return None

    # PySide6 6.11+: QKeySequence[int] returns a QKeyCombination, not int
    combo = ks[0]
    key = int(combo.key())
    modifiers = combo.keyboardModifiers()

    win32_mods = _qt_modifiers_to_win32(modifiers)
    vkey = _qt_key_to_win32_vkey(key)

    if vkey is None:
        logger.warning("Unsupported key code %d in sequence '%s'", key, sequence)
        return None

    return win32_mods, vkey


class GlobalHotkeyManager(QObject):
    """Manages system-wide hotkeys using Win32 RegisterHotKey API.

    Hotkeys are registered on a background thread that runs a Win32 message
    loop. When a hotkey is pressed, the hotkeyPressed signal is emitted
    on the main thread via Qt's signal/slot mechanism.

    IMPORTANT: Win32 RegisterHotKey must be called from the same thread
    that runs the message loop (PeekMessageW), otherwise WM_HOTKEY
    messages are posted to the wrong thread's queue.

    Only works on Windows (win32). On other platforms, all methods are no-ops.
    """

    hotkeyPressed = Signal(int)  # noqa: N815 — Emits hotkey ID when pressed

    def __init__(self, parent=None):
        super().__init__(parent)
        self._registered: dict[int, tuple[int, int]] = {}  # id -> (mods, vkey)
        self._listener_thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._sync_event = threading.Event()
        self._lock = threading.Lock()
        self._is_running = False

    @Slot(int, str)
    def register(self, hotkey_id: int, sequence: str):
        """Register a global hotkey from a QKeySequence string.

        Defers Win32 registration to the background thread so that
        RegisterHotKey and PeekMessageW run on the same thread.

        Args:
            hotkey_id: Unique identifier for this hotkey.
            sequence: Key sequence string like "Ctrl+Shift+S".
        """
        if sys.platform != "win32":
            logger.debug("Global hotkeys not supported on this platform")
            return

        parsed = parse_key_sequence(sequence)
        if parsed is None:
            logger.error("Failed to parse key sequence: %s", sequence)
            return

        with self._lock:
            self._registered[hotkey_id] = parsed
            self._sync_event.set()
            logger.info("Queued global hotkey id=%d: %s", hotkey_id, sequence)

    @Slot(int)
    def unregister(self, hotkey_id: int):
        """Unregister a global hotkey by ID."""
        if sys.platform != "win32":
            return

        with self._lock:
            if hotkey_id in self._registered:
                del self._registered[hotkey_id]
                self._sync_event.set()
                logger.info("Queued unregister for hotkey id=%d", hotkey_id)

    def start(self):
        """Start the background listener thread."""
        if sys.platform != "win32":
            logger.debug("Global hotkey listener not supported on this platform")
            return

        if self._is_running:
            return

        self._stop_event.clear()
        self._sync_event.set()  # Force initial registration sync
        self._listener_thread = threading.Thread(
            target=self._listen_loop, daemon=True, name="GlobalHotkeyListener"
        )
        self._listener_thread.start()
        self._is_running = True
        logger.info("Global hotkey listener started")

    def stop(self):
        """Stop the background listener thread and unregister all hotkeys."""
        if sys.platform != "win32":
            return

        self._stop_event.set()

        with self._lock:
            self._registered.clear()

        if self._listener_thread and self._listener_thread.is_alive():
            self._listener_thread.join(timeout=2.0)

        self._is_running = False
        logger.info("Global hotkey listener stopped")

    # --- Win32 API helpers (only called from background thread) ---

    def _register_win32(self, hotkey_id: int, mods: int, vkey: int) -> bool:
        """Register a hotkey with the Win32 API (background thread only)."""
        try:
            user32 = ctypes.windll.user32
            result = user32.RegisterHotKey(None, hotkey_id, mods | MOD_NOREPEAT, vkey)
            success = bool(result)
            if success:
                logger.info("Registered global hotkey id=%d", hotkey_id)
            else:
                logger.error("Failed to register global hotkey id=%d", hotkey_id)
            return success
        except Exception:
            logger.error("RegisterHotKey failed for id=%d", hotkey_id, exc_info=True)
            return False

    def _unregister_win32(self, hotkey_id: int):
        """Unregister a hotkey with the Win32 API (background thread only)."""
        try:
            user32 = ctypes.windll.user32
            user32.UnregisterHotKey(None, hotkey_id)
        except Exception:
            logger.warning("UnregisterHotKey failed for id=%d", hotkey_id, exc_info=True)

    def _sync_win32_registrations(self):
        """Sync the in-memory _registered dict with Win32 API.

        Called from the background thread only.
        Unregisters hotkeys that were removed, registers new ones.
        """
        with self._lock:
            wanted = dict(self._registered)

        # These are tracked on the background thread side only
        currently = {}
        if hasattr(self, "_background_registered"):
            currently = dict(self._background_registered)

        # Unregister removed hotkeys
        for hkid in list(currently.keys()):
            if hkid not in wanted:
                self._unregister_win32(hkid)
                del currently[hkid]

        # Register new hotkeys
        for hkid, (mods, vkey) in wanted.items():
            if hkid not in currently and self._register_win32(hkid, mods, vkey):
                currently[hkid] = (mods, vkey)

        self._background_registered = currently

    def _listen_loop(self):
        """Background thread: Win32 message loop listening for WM_HOTKEY.

        Win32 registration and message retrieval run on the same thread
        so that WM_HOTKEY messages are delivered correctly.
        """
        logger.info("Hotkey listener thread running (id=%d)", threading.get_ident())

        self._background_registered: dict[int, tuple[int, int]] = {}
        self._sync_win32_registrations()

        msg = wintypes.MSG()
        user32 = ctypes.windll.user32

        while not self._stop_event.is_set():
            # Re-sync if registrations changed from the main thread
            if self._sync_event.is_set():
                self._sync_event.clear()
                self._sync_win32_registrations()

            # PeekMessage with PM_REMOVE so we can check _stop_event periodically
            result = user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, 0x0001)  # PM_REMOVE
            if result:
                if msg.message == WM_HOTKEY:
                    hotkey_id = msg.wParam
                    logger.info("Global hotkey pressed: id=%d", hotkey_id)
                    # Emit signal on the main thread via Qt's signal mechanism
                    self.hotkeyPressed.emit(hotkey_id)
            else:
                # No message available, wait for one
                user32.WaitMessage()

        # Cleanup: unregister all hotkeys on this thread
        for hkid in list(self._background_registered.keys()):
            self._unregister_win32(hkid)
        self._background_registered.clear()
        logger.info("Hotkey listener thread exiting")
