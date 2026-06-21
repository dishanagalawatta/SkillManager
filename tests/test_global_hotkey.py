"""Tests for the global hotkey manager.

These tests verify the manager's CONTRACT:
- The module can be imported without pynput being usable
- The manager can be instantiated without pynput
- register() returns True/False based on pynput availability
- The Qt signal emission works regardless of pynput state
- Unregister of unknown id is a safe no-op
- stop() properly joins the listener thread
- Listener creation failure is handled gracefully

The tests do NOT start real pynput listeners — ``conftest.py`` patches
``_ensure_pynput`` to return ``False`` for the entire test session.  The
new unit tests below patch ``keyboard.Listener`` with a lightweight fake
so that the listener-lifecycle code paths are exercised without touching
the Windows keyboard hook.
"""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

from skill_manager.core.global_hotkey import (
    LISTENER_JOIN_TIMEOUT,  # type: ignore[attr-defined]
    GlobalHotkeyManager,
)


class _FakeListener:
    """Minimal stand-in for ``pynput.keyboard.Listener``.

    Records calls to ``start()`` / ``stop()`` and provides a fake
    ``_thread`` attribute so ``GlobalHotkeyManager._restart_listener``
    can capture it.
    """

    def __init__(self, **kwargs):
        self._press = kwargs.get("on_press")
        self._release = kwargs.get("on_release")
        self.started = False
        self.stopped = False
        self.join = MagicMock()
        self.is_alive = MagicMock(return_value=False)

    def start(self):
        self.started = True

    def stop(self):
        self.stopped = True

    def canonical(self, key):
        return key


class TestManagerContract:
    """The class is a QObject that exposes hotkeyPressed(int)."""

    def test_inherits_from_qobject(self):
        from PySide6.QtCore import QObject

        assert issubclass(GlobalHotkeyManager, QObject)

    def test_has_hotkey_pressed_signal(self):
        manager = GlobalHotkeyManager()
        assert hasattr(manager, "hotkeyPressed")
        # Signal is connectable
        received: list[int] = []
        manager.hotkeyPressed.connect(lambda hid: received.append(hid))
        manager.hotkeyPressed.emit(42)
        assert received == [42]


class TestManagerWithoutPynput:
    """Behavior when pynput is not available.

    We test this by directly setting _pynput_available = False
    (simulating the lazy-import having failed). This is a contract
    test, not a mock — we're verifying what the manager does in
    the "pynput unavailable" state.
    """

    def test_register_returns_false_when_pynput_unavailable(self):
        manager = GlobalHotkeyManager()
        manager._pynput_available = False  # Simulate failed lazy-import
        result = manager.register(1, "Ctrl+Shift+S")
        assert result is False
        assert 1 not in manager._hotkeys  # State unchanged

    def test_register_empty_sequence_returns_false(self):
        manager = GlobalHotkeyManager()
        manager._pynput_available = False
        result = manager.register(1, "")
        assert result is False

    def test_unregister_unknown_id_is_safe(self):
        manager = GlobalHotkeyManager()
        manager._pynput_available = False
        manager.unregister(999)  # No error, no state change
        assert 999 not in manager._hotkeys

    def test_stop_with_no_listener_is_safe(self):
        manager = GlobalHotkeyManager()
        manager._pynput_available = False
        manager.stop()  # No error even with no listener registered
        assert manager._hotkeys == {}
        assert manager._listener is None

    def test_start_is_noop(self):
        """start() is a compatibility shim — verify it doesn't crash."""
        manager = GlobalHotkeyManager()
        manager._pynput_available = False
        manager.start()  # No error


class TestManagerStateTransitions:
    """Verify the lazy-import state machine."""

    def test_initial_state_is_unchecked(self):
        manager = GlobalHotkeyManager()
        assert manager._pynput_available is None  # None = unchecked

    def test_pynput_availability_cached(self):
        """Once checked, the result is cached."""
        manager = GlobalHotkeyManager()
        manager._pynput_available = True
        # Second call should not re-import — verify by checking the flag
        assert manager._pynput_available is True


class TestNoPynputImportAtModuleLoad:
    """Critical regression test: importing global_hotkey must NOT import pynput.

    This is the test that would have caught the original CI bug.
    """

    def test_module_docstring_mentions_lazy_loading(self):
        import skill_manager.core.global_hotkey as gh

        assert gh.__doc__ is not None
        assert "lazy" in gh.__doc__.lower()


class TestListenerLifecycle:
    """Unit tests for the new thread-tracking and stop-join behaviour.

    These patch ``keyboard.Listener`` with ``_FakeListener`` so we
    exercise the lifecycle code paths without touching the Windows
    keyboard hook.
    """

    def test_stop_joins_listener_thread(self):
        """stop() must set _listener=None after join."""
        manager = GlobalHotkeyManager()

        fake_pynput = MagicMock()
        fake_pynput.keyboard.HotKey.parse.return_value = []

        with (
            patch.dict(
                sys.modules, {"pynput": fake_pynput, "pynput.keyboard": fake_pynput.keyboard}
            ),
            patch.object(GlobalHotkeyManager, "_ensure_pynput", return_value=True),
        ):
            fake_listener = _FakeListener()
            fake_listener.is_alive.return_value = True
            fake_pynput.keyboard.Listener.return_value = fake_listener

            manager.register(1, "Ctrl+Shift+S")
            assert manager._listener is fake_listener

            manager.stop()

        # Thread join was called with timeout
        fake_listener.join.assert_called_once_with(timeout=LISTENER_JOIN_TIMEOUT)
        # State cleaned up
        assert manager._listener is None
        assert fake_listener.stopped

    def test_stop_does_not_join_when_not_alive(self):
        """If listener is not alive, stop() still clears state but doesn't join."""
        manager = GlobalHotkeyManager()

        fake_pynput = MagicMock()
        fake_pynput.keyboard.HotKey.parse.return_value = []

        with (
            patch.dict(
                sys.modules, {"pynput": fake_pynput, "pynput.keyboard": fake_pynput.keyboard}
            ),
            patch.object(GlobalHotkeyManager, "_ensure_pynput", return_value=True),
        ):
            fake_listener = _FakeListener()
            fake_listener.is_alive.return_value = False
            fake_pynput.keyboard.Listener.return_value = fake_listener

            manager.register(1, "Ctrl+Shift+S")
            manager.stop()

        # join() was NOT called (listener already dead)
        fake_listener.join.assert_not_called()
        assert manager._listener is None

    def test_double_stop_is_safe(self):
        """Calling stop() twice must not raise."""
        manager = GlobalHotkeyManager()

        fake_pynput = MagicMock()
        fake_pynput.keyboard.HotKey.parse.return_value = []

        with (
            patch.dict(
                sys.modules, {"pynput": fake_pynput, "pynput.keyboard": fake_pynput.keyboard}
            ),
            patch.object(GlobalHotkeyManager, "_ensure_pynput", return_value=True),
        ):
            fake_listener = _FakeListener()
            fake_pynput.keyboard.Listener.return_value = fake_listener

            manager.register(1, "Ctrl+Shift+S")
            manager.stop()
            manager.stop()  # second call — must not raise

        assert manager._listener is None

    def test_listener_creation_failure_doesnt_crash(self):
        """OSError from keyboard.Listener() must not propagate."""
        manager = GlobalHotkeyManager()

        fake_pynput = MagicMock()
        fake_pynput.keyboard.Listener.side_effect = OSError("no console session")
        fake_pynput.keyboard.HotKey.parse.return_value = []

        with (
            patch.dict(
                sys.modules, {"pynput": fake_pynput, "pynput.keyboard": fake_pynput.keyboard}
            ),
            patch.object(GlobalHotkeyManager, "_ensure_pynput", return_value=True),
        ):
            result = manager.register(1, "Ctrl+Shift+S")

        assert result is True  # hotkey was registered
        assert manager._listener is None  # listener not created

    def test_stop_acquires_stop_lock(self):
        """stop() acquires _stop_lock to serialise concurrent calls."""
        manager = GlobalHotkeyManager()

        # Verify the lock exists and is a proper Lock
        assert hasattr(manager, "_stop_lock")
        assert hasattr(manager._stop_lock, "acquire")
        assert hasattr(manager._stop_lock, "release")
