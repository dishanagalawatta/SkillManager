"""Global hotkey manager using pynput (lazy-loaded).

Architecture:
- Pure key-sequence conversion lives in ``skill_manager.core.keymap``
- pynput is lazy-imported only when ``register()`` is called
- Graceful degradation: if pynput is unavailable, ``register()`` returns
  ``False`` and the app continues to function (snap hotkey is the
  only feature using this)

Per pynput's official documentation, the recommended pattern for
hotkey sets that can change at runtime is ``HotKey`` + ``Listener``
(rather than ``GlobalHotKeys``, which is optimized for a fixed mapping).
"""

from __future__ import annotations

import logging
import os
import sys
import threading
from collections.abc import Callable
from enum import IntEnum
from typing import TYPE_CHECKING, Any

from PySide6.QtCore import Property, QObject, Signal, Slot

from skill_manager.core.keymap import (
    qt_sequence_to_pynput_keys,
)
from skill_manager.core.portal_hotkey_backend import (
    PORTAL_HELPER_STOP_TIMEOUT as PORTAL_HELPER_STOP_TIMEOUT,
    PortalHotkeyBackend as PortalHotkeyBackend,
)

if TYPE_CHECKING:
    from pynput import keyboard  # noqa: F401

logger = logging.getLogger(__name__)

LISTENER_JOIN_TIMEOUT = 2.0


class HotkeyId(IntEnum):
    """Registry of global hotkey identifiers."""

    SNAP = 1


def detect_environment_and_display() -> tuple[str, bool, str]:
    """Detect current runtime environment, platform, display server, and permission capability.

    Returns:
        tuple of (environment_name, hotkeys_supported, status_reason)
    """
    if os.environ.get("SKILL_MANAGER_TESTING") == "1":
        return "Testing", False, "Global hotkeys disabled in test mode"

    qt_platform = os.environ.get("QT_QPA_PLATFORM", "").lower()
    if qt_platform in ("offscreen", "minimal", "vnc", "linuxfb"):
        return (
            f"Headless ({qt_platform})",
            False,
            f"Global hotkeys unavailable on {qt_platform} platform",
        )

    if sys.platform.startswith("linux"):
        display = os.environ.get("DISPLAY")
        wayland = os.environ.get("WAYLAND_DISPLAY")

        if not display and not wayland:
            return (
                "Headless (Linux)",
                False,
                "Global hotkeys unavailable: No X11 or Wayland display server connected",
            )

        session_type = os.environ.get("XDG_SESSION_TYPE", "").lower()
        if session_type == "wayland" or wayland:
            if not display:
                return (
                    "Wayland",
                    False,
                    "Global hotkeys unavailable: Wayland session requires XWayland ($DISPLAY)",
                )
            return "Wayland (XWayland)", True, "Global hotkeys active via XWayland"

        return "X11", True, "Global hotkeys active via X11"

    if sys.platform == "win32":
        return "Windows", True, "Global hotkeys active via Win32 API"

    if sys.platform == "darwin":
        return "macOS", True, "Global hotkeys active via macOS Accessibility"

    return sys.platform, True, "Global hotkeys supported"


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
    availabilityChanged = Signal()  # noqa: N815

    def __init__(self, parent=None):
        super().__init__(parent)
        self._hotkeys: dict[int, tuple[str, str]] = {}  # id -> (pynput_seq, original)
        self._listener = None
        self._lock = threading.Lock()
        self._stop_lock = threading.Lock()
        self._pynput_available: bool | None = None  # None = unchecked
        self._availability_reason: str = "Unchecked"
        self._cleaned_up = False
        self._portal_backend: PortalHotkeyBackend | None = None
        self._portal_available: bool | None = None  # None = unchecked

        self._config_controller: Any = None
        self._snap_controller: Any = None
        self._get_window_active: Callable[[], bool] | None = None
        self._snap_hotkey_id: int = HotkeyId.SNAP

    def setup_snap_hotkey(
        self,
        config_controller: Any,
        snap_controller: Any,
        get_window_active: Callable[[], bool],
        hotkey_id: int = HotkeyId.SNAP,
    ) -> None:
        """Register global snap hotkey and connect update signals."""
        from PySide6.QtCore import Qt

        self._config_controller = config_controller
        self._snap_controller = snap_controller
        self._get_window_active = get_window_active
        self._snap_hotkey_id = hotkey_id

        # Use QueuedConnection because the signal is emitted from a background thread
        self.hotkeyPressed.connect(self._on_snap_hotkey_pressed, Qt.ConnectionType.QueuedConnection)

        snap_seq = config_controller.get_shortcut("snap")
        if snap_seq and config_controller.isShortcutEnabled("snap"):
            self.register(hotkey_id, snap_seq)

        config_controller.shortcutsChanged.connect(self._on_shortcuts_changed_snap)
        self.start()

    def _is_window_active(self) -> bool:
        if self._get_window_active is None:
            return False
        target = getattr(self._get_window_active, "__self__", None)
        name = getattr(self._get_window_active, "__name__", None)
        if target is not None and name is not None:
            return bool(getattr(target, name)())
        return bool(self._get_window_active())

    @Slot(int)
    def _on_snap_hotkey_pressed(self, hotkey_id: int) -> None:
        """Handle snap hotkey press with double-fire prevention."""
        if hotkey_id == self._snap_hotkey_id:
            if not self.portalBackendActive and self._is_window_active():
                logger.debug("[HOTKEY] global snap skipped: main window focused")
                return
            if self._snap_controller:
                self._snap_controller.takeSnap()

    def _on_shortcuts_changed_snap(self) -> None:
        """Re-register snap hotkey when shortcuts change."""
        if not self._config_controller:
            return
        snap_seq = self._config_controller.get_shortcut("snap")
        if snap_seq and self._config_controller.isShortcutEnabled("snap"):
            self.register(self._snap_hotkey_id, snap_seq)
        else:
            self.unregister(self._snap_hotkey_id)

    @Property(bool, notify=availabilityChanged)
    def isAvailable(self) -> bool:  # noqa: N802
        """Returns True if global hotkeys are supported and active in the current environment."""
        env_name, _, _ = detect_environment_and_display()
        if "Wayland" in env_name:
            return self._ensure_portal() or self._ensure_pynput()
        return self._ensure_pynput() or self._ensure_portal()

    @Property(str, notify=availabilityChanged)
    def statusReason(self) -> str:  # noqa: N802
        """Returns a human-readable explanation of global hotkey availability."""
        env_name, _, _ = detect_environment_and_display()
        if "Wayland" in env_name:
            if self._ensure_portal():
                return self._availability_reason
            self._ensure_pynput()
            return self._availability_reason
        self._ensure_pynput()
        if not self._pynput_available:
            self._ensure_portal()
        return self._availability_reason

    @Property(bool, notify=availabilityChanged)
    def portalBackendActive(self) -> bool:  # noqa: N802
        """Return True when the Wayland portal backend is the active backend.

        The pynput listener (X11/XWayland) observes keys passively, so a
        pressed hotkey ALSO reaches the focused app window and the in-app
        QML ``Shortcut`` fires — a double-fire guard is required.  The
        portal backend instead grabs the key at the compositor, so the
        focused window never receives the keypress: the portal signal is
        the ONLY path, and callers must not skip it.
        """
        return self._portal_backend is not None

    def _ensure_pynput(self) -> bool:
        """Lazy-import pynput. Returns True if usable, False if not."""
        if self._pynput_available is not None:
            return self._pynput_available

        env_name, supported, reason = detect_environment_and_display()
        if not supported:
            logger.info("Global hotkeys disabled for environment '%s': %s", env_name, reason)
            self._availability_reason = reason
            self._pynput_available = False
            self.availabilityChanged.emit()
            return False

        try:
            from pynput import keyboard  # noqa: F401

            self._pynput_available = True
            self._availability_reason = reason
        except Exception as e:
            err_msg = str(e).split("\n")[0].strip()
            if (
                "authorization required" in err_msg.lower()
                or "can't connect to display" in err_msg.lower()
            ):
                clean_reason = "Global hotkeys unavailable: X11 display connection unauthorized"
            elif "import" in err_msg.lower() or "module" in err_msg.lower():
                clean_reason = "Global hotkeys unavailable: pynput package not installed"
            else:
                clean_reason = f"Global hotkeys unavailable: {err_msg}"

            logger.info(
                "Global hotkeys probe result for environment '%s': %s", env_name, clean_reason
            )
            try:
                from skill_manager.core.diagnostics import get_diagnostic_logger

                get_diagnostic_logger().log_event(
                    "INFO",
                    "global_hotkey_env",
                    clean_reason,
                    data={"environment": env_name, "raw_error": err_msg},
                )
            except Exception:
                pass

            self._pynput_available = False
            self._availability_reason = clean_reason

        self.availabilityChanged.emit()
        return self._pynput_available

    def _ensure_portal(self) -> bool:
        """Lazy-start the portal backend on Wayland. Returns True if usable."""
        if self._portal_available is not None:
            return self._portal_available

        if os.environ.get("SKILL_MANAGER_TESTING") == "1":
            self._portal_available = False
            return False

        env_name, _, _ = detect_environment_and_display()
        if "Wayland" not in env_name:
            self._portal_available = False
            return False

        backend = PortalHotkeyBackend(self)
        if not backend.start():
            self._availability_reason = "Global hotkeys unavailable: portal backend failed to start"
            self._portal_available = False
            return False

        self._portal_backend = backend
        backend.hotkeyPressed.connect(self.hotkeyPressed)  # re-emit
        self._portal_available = True
        self._availability_reason = "Global hotkeys active via portal backend"
        self.availabilityChanged.emit()
        return True

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
            self._listener.start()
        except OSError as e:
            logger.error("Failed to start pynput listener: %s", e)
            self._listener = None

    def _stop_active_listener(self) -> None:
        """Stop the current listener and join its thread with a timeout.

        Uses ``_stop_lock`` so concurrent calls are serialised.  If the
        join times out the thread is left as a daemon and will be killed
        when the interpreter exits — no crash, no hang.
        """
        with self._stop_lock:
            listener = self._listener
            self._listener = None

        if listener is None:
            return

        try:
            listener.stop()
        except Exception:  # noqa: BLE001 — defensive
            logger.debug("Error stopping pynput listener", exc_info=True)

        if listener.is_alive():
            try:
                listener.join(timeout=LISTENER_JOIN_TIMEOUT)
            except Exception as e:
                logger.debug("Exception during pynput listener join: %s", e)

            if listener.is_alive():
                logger.warning(
                    "pynput listener thread did not exit within %ss; leaving as daemon",
                    LISTENER_JOIN_TIMEOUT,
                )

    @Slot(int, str)
    def register(self, hotkey_id: int, sequence: str) -> bool:
        """Register a global hotkey from a QKeySequence string.

        Prefers the FreeDesktop portal GlobalShortcuts backend on Wayland;
        prefers pynput on X11, Windows, and macOS.

        Args:
            hotkey_id: Unique identifier for this hotkey.
            sequence: Key sequence string like "Ctrl+Shift+S".

        Returns:
            True if registered, False if neither backend is available
            or sequence is empty.
        """
        if not sequence:
            return False

        # Clear any stale pynput binding for this hotkey_id to prevent dual-activation
        with self._lock:
            if self._hotkeys.pop(hotkey_id, None) is not None:
                self._restart_listener()

        env_name, _, _ = detect_environment_and_display()
        if "Wayland" in env_name:
            if self._ensure_portal():
                return self._portal_backend.register(hotkey_id, sequence)
            if self._ensure_pynput():
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
            return False

        if self._ensure_pynput():
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
        if self._ensure_portal():
            return self._portal_backend.register(hotkey_id, sequence)
        return False

    @Slot(int)
    def unregister(self, hotkey_id: int) -> None:
        """Unregister a global hotkey by ID."""
        with self._lock:
            if hotkey_id in self._hotkeys:
                del self._hotkeys[hotkey_id]
                logger.info("Unregistered global hotkey id=%d", hotkey_id)
                self._restart_listener()
        if self._portal_backend is not None:
            self._portal_backend.unregister(hotkey_id)

    def start(self) -> None:
        """Start method retained for compatibility. Registration occurs immediately."""
        logger.info("Global hotkey manager started")

    def stop(self) -> None:
        """Unregister all hotkeys and stop listener/portal backend. Idempotent."""
        if self._cleaned_up:
            return
        self._cleaned_up = True
        with self._lock:
            self._hotkeys.clear()
        self._stop_active_listener()
        if self._portal_backend is not None:
            self._portal_backend.stop()
            self._portal_backend = None
            self._portal_available = None  # re-probe on next register
        logger.info("Global hotkey manager stopped")

    def on_hotkey_pressed(self, hotkey_id: int) -> None:
        """Callback executed by the pynput library when a hotkey triggers.

        This executes on a background thread. Emitting a Qt Signal from here
        safely marshals the call to the Qt main thread event loop.
        """
        logger.info("Global hotkey triggered: id=%d", hotkey_id)
        self.hotkeyPressed.emit(hotkey_id)


def _make_callback(manager: GlobalHotkeyManager, hotkey_id: int):
    """Build a closure that calls ``on_hotkey_pressed`` on the manager.

    Pynput invokes the registered callable with no arguments; we use
    a closure factory to bind the hotkey_id at registration time.
    """

    def callback():
        manager.on_hotkey_pressed(hotkey_id)

    return callback
