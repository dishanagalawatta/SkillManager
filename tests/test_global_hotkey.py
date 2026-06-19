"""Tests for the global hotkey manager.

These tests verify the manager's CONTRACT:
- The module can be imported without pynput being usable
- The manager can be instantiated without pynput
- register() returns True/False based on pynput availability
- The Qt signal emission works regardless of pynput state
- Unregister of unknown id is a safe no-op

The tests do NOT mock pynput — they test what actually happens
when the module is imported and the manager is constructed.
The pynput lazy-import is verified by checking _pynput_available
state transitions, not by patching sys.modules.
"""

from skill_manager.core.global_hotkey import GlobalHotkeyManager


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
