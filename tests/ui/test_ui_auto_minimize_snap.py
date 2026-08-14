"""Regression tests for auto-minimize on Snap (snap).

The window must hide via a REAL minimize (``showMinimized``), not via
``opacity = 0``: Qt's Wayland platform plugin ignores window opacity, so
the old approach left the window fully visible — and inside its own
snap — on Wayland (and non-compositing X11).

Note on Qt semantics: a minimized top-level window still reports
``visible == true``; the compositor stops rendering it (that is what
excludes it from screen captures). The correct state assertion is
``visibility == Visibility.Minimized``.
"""

import pytest
from PySide6.QtCore import QMetaObject, QObject, Qt
from PySide6.QtGui import QWindow


def _window(qml_engine):
    return qml_engine.rootObjects()[0]


def _invoke(obj, method: str) -> bool:
    return bool(QMetaObject.invokeMethod(obj, method, Qt.DirectConnection))


def _snap_button(window):
    for child in window.findChildren(QObject):
        if child.objectName() == "topSnapBtn":
            return child
    raise AssertionError("topSnapBtn not found in window")


def _overlay_window(window):
    for child in window.findChildren(QObject):
        if child.objectName() == "snapOverlayWindow":
            return child
    return None


@pytest.mark.usefixtures("setup_qml_style")
class TestUIAutoMinimizeSnap:
    def test_minimize_for_snap_hides_via_minimize_not_opacity(self, qml_engine, qtbot):
        window = _window(qml_engine)
        window.show()
        qtbot.wait(50)

        _invoke(window, "minimizeWindowInstantly")

        # The window must be truly unmapped by the compositor —
        # not just made transparent.
        assert window.property("visibility") == QWindow.Visibility.Hidden

        # Regression guard: opacity must NOT be the hide mechanism.
        assert window.property("opacity") == 1.0

    def test_restore_window_state_restores_visibility_and_geometry(self, qml_engine, qtbot):
        window = _window(qml_engine)
        window.setProperty("x", 123)
        window.setProperty("y", 45)
        window.setProperty("width", 700)
        window.setProperty("height", 500)
        window.show()
        qtbot.wait(50)

        _invoke(window, "saveWindowState")
        _invoke(window, "minimizeWindowInstantly")
        assert window.property("visibility") == QWindow.Visibility.Hidden

        _invoke(window, "restoreWindowState")
        qtbot.wait(50)

        assert window.property("visibility") == QWindow.Visibility.Windowed
        assert window.property("x") == 123
        assert window.property("y") == 45
        assert window.property("width") == 700
        assert window.property("height") == 500

    def test_snap_click_with_auto_minimize_minimizes_then_restores(
        self, qml_engine, app_controller, qtbot
    ):
        window = _window(qml_engine)
        window.show()
        qtbot.wait(50)
        app_controller.config_controller.autoMinimizeOnSnap = True

        overlay_fired = []
        app_controller.snap_controller.showOverlay.connect(lambda: overlay_fired.append(True))

        _invoke(_snap_button(window), "click")

        # Immediately after the click the window is hidden.
        assert window.property("visibility") == QWindow.Visibility.Hidden

        # After the capture delay, overlay is shown and window remains minimized during capture.
        qtbot.waitUntil(lambda: bool(overlay_fired), timeout=3000)
        assert window.property("pendingSnap") is True

        # When capture is cancelled or completed, the window is restored to windowed focus.
        app_controller.snap_controller.cancelCapture()
        qtbot.waitUntil(
            lambda: window.property("visibility") == QWindow.Visibility.Windowed,
            timeout=3000,
        )
        assert window.property("pendingSnap") is False

    def test_snap_click_with_auto_minimize_shows_overlay_window(
        self, qml_engine, app_controller, qtbot
    ):
        """Regression guard: after auto-minimize the overlay QML window must
        be shown (visible + windowed), not left hidden."""
        window = _window(qml_engine)
        window.show()
        qtbot.wait(50)
        app_controller.config_controller.autoMinimizeOnSnap = True

        overlay_fired = []
        app_controller.snap_controller.showOverlay.connect(lambda: overlay_fired.append(True))

        _invoke(_snap_button(window), "click")

        qtbot.waitUntil(lambda: bool(overlay_fired), timeout=3000)

        overlay = _overlay_window(window)
        assert overlay is not None, "snapOverlayWindow not found in window"
        qtbot.waitUntil(lambda: overlay.property("visible") is True, timeout=3000)
        assert overlay.property("visibility") == QWindow.Visibility.Windowed
        assert window.property("pendingSnap") is True

    def test_snap_click_without_auto_minimize_does_not_minimize(
        self, qml_engine, app_controller, qtbot
    ):
        window = _window(qml_engine)
        window.show()
        qtbot.wait(50)
        app_controller.config_controller.autoMinimizeOnSnap = False

        overlay_fired = []
        app_controller.snap_controller.showOverlay.connect(lambda: overlay_fired.append(True))

        _invoke(_snap_button(window), "click")

        # No minimize path: capture starts immediately, window stays windowed.
        qtbot.waitUntil(lambda: bool(overlay_fired), timeout=3000)
        assert window.property("visibility") == QWindow.Visibility.Windowed
        assert window.property("opacity") == 1.0

    def test_snap_while_manually_minimized_keeps_main_window_in_background(
        self, qml_engine, app_controller, qtbot
    ):
        """Snapping while the main app is in background or minimized (pendingSnap == False)
        must show the overlay immediately without un-minimizing or raising the main window."""
        window = _window(qml_engine)
        window.show()
        qtbot.wait(50)

        # Simulate the user manually minimizing the app (no pendingSnap).
        window.showMinimized()
        qtbot.wait(50)
        assert window.property("visibility") == QWindow.Visibility.Minimized
        assert window.property("pendingSnap") is False

        overlay_fired = []
        app_controller.snap_controller.showOverlay.connect(lambda: overlay_fired.append(True))

        # Emit directly — global hotkey path triggers showOverlay signal.
        app_controller.snap_controller.showOverlay.emit()

        overlay = _overlay_window(window)
        assert overlay is not None, "snapOverlayWindow not found in window"
        qtbot.waitUntil(lambda: overlay.property("visible") is True, timeout=3000)

        # Main window must remain minimized in background.
        assert window.property("visibility") == QWindow.Visibility.Minimized
        assert bool(overlay_fired)

    def test_closing_snap_overlay_does_not_trigger_app_quit(
        self, qml_engine, app_controller, qtbot, monkeypatch
    ):
        """Regression guard: closing SnapOverlay while main window is minimized must NOT
        trigger QGuiApplication shutdown or controller.on_quit()."""
        quit_called = []
        monkeypatch.setattr(app_controller, "on_quit", lambda: quit_called.append(True))

        window = _window(qml_engine)
        window.show()
        qtbot.wait(50)
        app_controller.config_controller.autoMinimizeOnSnap = True

        overlay_fired = []
        app_controller.snap_controller.showOverlay.connect(lambda: overlay_fired.append(True))

        _invoke(_snap_button(window), "click")
        qtbot.waitUntil(lambda: bool(overlay_fired), timeout=3000)

        overlay = _overlay_window(window)
        assert overlay is not None, "snapOverlayWindow not found"
        qtbot.waitUntil(lambda: overlay.property("visible") is True, timeout=3000)

        # Close the overlay (simulating user canceling/finishing snap)
        overlay.close()
        qtbot.wait(100)

        # AppController.on_quit MUST NOT have been called
        assert not quit_called, "Closing overlay triggered on_quit shutdown!"
