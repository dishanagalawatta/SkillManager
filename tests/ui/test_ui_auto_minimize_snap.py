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

        # The window must be truly minimized (unmapped by the compositor) —
        # not just made transparent.
        assert window.property("visibility") == QWindow.Visibility.Minimized

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
        assert window.property("visibility") == QWindow.Visibility.Minimized

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

        # Immediately after the click the window is minimized.
        assert window.property("visibility") == QWindow.Visibility.Minimized

        # After the 150 ms capture delay the window is restored (windowed)
        # and the capture overlay has been shown.
        qtbot.waitUntil(lambda: bool(overlay_fired), timeout=3000)
        qtbot.waitUntil(
            lambda: window.property("visibility") == QWindow.Visibility.Windowed,
            timeout=3000,
        )
        assert window.property("pendingSnap") is True

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
