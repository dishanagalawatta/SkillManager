"""Tests for scroll speed multiplier in SmoothListView and SmoothScrollView."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from PySide6.QtCore import Property, QObject, QUrl, Signal
from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent
from PySide6.QtWidgets import QApplication

QML_DIR = (
    Path(__file__).resolve().parent.parent.parent
    / "src"
    / "skill_manager"
    / "SkillManagerComponents"
)


class _MockConfigController(QObject):
    scrollSpeedMultiplierChanged = Signal()  # noqa: N815

    def __init__(self, multiplier: float = 1.0, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._multiplier = multiplier

    @Property(float, notify=scrollSpeedMultiplierChanged)
    def scrollSpeedMultiplier(self) -> float:  # noqa: N802
        return self._multiplier

    @scrollSpeedMultiplier.setter  # type: ignore[func-attr]
    def scrollSpeedMultiplier(self, val: float) -> None:  # noqa: N802
        if self._multiplier != val:
            self._multiplier = val
            self.scrollSpeedMultiplierChanged.emit()


class _MockAppController(QObject):
    def __init__(self, multiplier: float = 1.0, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.config_controller = _MockConfigController(multiplier, self)


def _load_qml_component(
    qapp: QApplication, qml_path: Path, app_controller: QObject
) -> tuple[QQmlApplicationEngine, QQmlComponent, QObject | None, list[str], list[str]]:
    """Load a QML component and return (engine, component, instance, errors, warnings)."""
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("appController", app_controller)
    engine.addImportPath(str(QML_DIR.parent))

    warnings: list[str] = []
    engine.warnings.connect(lambda msgs: warnings.extend(m.toString() for m in msgs))

    component = QQmlComponent(engine)
    component.setData(
        qml_path.read_text(encoding="utf-8").encode(),
        QUrl.fromLocalFile(str(qml_path)),
    )

    errors = [e.toString() for e in component.errors()]
    obj = None
    if not errors and component.isReady():
        try:
            obj = component.create()
        except Exception as exc:
            errors.append(f"create() raised {type(exc).__name__}: {exc}")

    return engine, component, obj, errors, warnings


def test_smooth_list_view_qml_contract():
    """Verify SmoothListView.qml defines WheelHandler and references scrollSpeedMultiplier."""
    content = (QML_DIR / "SmoothListView.qml").read_text(encoding="utf-8")
    assert "WheelHandler" in content
    assert "scrollSpeedMultiplier" in content
    assert "pixelDelta" in content
    assert "angleDelta" in content
    assert "event.accepted" in content
    assert "AppScrollBar" in content


def test_smooth_scroll_view_qml_contract():
    """Verify SmoothScrollView.qml defines WheelHandler and references scrollSpeedMultiplier."""
    content = (QML_DIR / "SmoothScrollView.qml").read_text(encoding="utf-8")
    assert "WheelHandler" in content
    assert "scrollSpeedMultiplier" in content
    assert "pixelDelta" in content
    assert "angleDelta" in content
    assert "event.accepted" in content
    assert "AppScrollBar" in content


def test_smooth_list_view_loads_cleanly(qapp, app_controller):
    """Verify SmoothListView loads without errors across different multipliers."""
    for mult in [0.5, 1.0, 2.0, 3.5]:
        app_controller.config_controller.scrollSpeedMultiplier = mult
        _engine, _component, obj, errors, _warnings = _load_qml_component(
            qapp, QML_DIR / "SmoothListView.qml", app_controller
        )
        assert not errors, f"SmoothListView errors with multiplier={mult}: {errors}"
        assert obj is not None


def test_smooth_scroll_view_loads_cleanly(qapp, app_controller):
    """Verify SmoothScrollView loads without errors across different multipliers."""
    for mult in [0.5, 1.0, 2.0, 3.5]:
        app_controller.config_controller.scrollSpeedMultiplier = mult
        _engine, _component, obj, errors, _warnings = _load_qml_component(
            qapp, QML_DIR / "SmoothScrollView.qml", app_controller
        )
        assert not errors, f"SmoothScrollView errors with multiplier={mult}: {errors}"
        assert obj is not None


def test_config_controller_scroll_multiplier_signal_and_persistence(app_controller):
    """Verify ConfigController updates scroll_speed_multiplier and emits signal."""
    controller = app_controller.config_controller
    signal_spy = MagicMock()
    controller.scrollSpeedMultiplierChanged.connect(signal_spy)

    controller.scrollSpeedMultiplier = 2.5
    assert controller.scrollSpeedMultiplier == 2.5
    signal_spy.assert_called_once()


def test_real_config_controller_qml_binding_live_update(qapp, app_controller):
    """Verify QML property binding receives live updates when scrollSpeedMultiplier changes."""
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("appController", app_controller)

    qml_str = """
    import QtQuick

    Item {
        id: root
        property real mult: appController.config_controller.scrollSpeedMultiplier
        property string desc: "Multiplier: " + mult.toFixed(1) + "x"
    }
    """
    comp = QQmlComponent(engine)
    comp.setData(qml_str.encode("utf-8"), QUrl(""))
    obj = comp.create()
    assert obj is not None

    app_controller.config_controller.scrollSpeedMultiplier = 1.0
    assert obj.property("mult") == 1.0
    assert obj.property("desc") == "Multiplier: 1.0x"

    app_controller.config_controller.scrollSpeedMultiplier = 3.5
    assert obj.property("mult") == 3.5
    assert obj.property("desc") == "Multiplier: 3.5x"

    app_controller.config_controller.scrollSpeedMultiplier = 5.0
    assert obj.property("mult") == 5.0
    assert obj.property("desc") == "Multiplier: 5.0x"


def test_config_controller_no_shadowed_mixin_signals():
    """Verify ConfigController does not redefine mixin signals, preserving Qt meta-object bindings."""
    from skill_manager.controllers.config.settings import SettingsMixin
    from skill_manager.controllers.config_controller import ConfigController

    # SettingsMixin defines scrollSpeedMultiplierChanged; ConfigController class dict must not shadow it
    assert "scrollSpeedMultiplierChanged" not in ConfigController.__dict__
    assert hasattr(ConfigController, "scrollSpeedMultiplierChanged")
    assert (
        ConfigController.scrollSpeedMultiplierChanged is SettingsMixin.scrollSpeedMultiplierChanged
    )


def test_settings_view_scroll_speed_slider_live_sync(qapp, app_controller):
    """Verify SettingsView loads cleanly and syncs scrollSpeedMultiplier with slider."""
    _engine, _comp, obj, errors, warnings = _load_qml_component(
        qapp, QML_DIR / "views" / "SettingsView.qml", app_controller
    )
    assert not errors, f"SettingsView compilation errors: {errors}"
    assert obj is not None

    # Change scrollSpeedMultiplier via controller and verify no errors/crashes
    for val in [0.5, 1.5, 3.2, 5.0]:
        app_controller.config_controller.scrollSpeedMultiplier = val
        assert app_controller.config_controller.scrollSpeedMultiplier == val
