"""Diagnostic test: load SettingsView and report exactly what's broken.

This test exists to give automatic feedback (no screenshots needed) when
the Settings view fails to render. It loads the QML with the same setup the
real app uses (Basic style, SkillManagerComponents import path) and reports:
  - QML compile errors with file + line
  - QML runtime warnings
  - Whether the root item has children
  - Whether the root item has a non-zero size

Run with:  uv run pytest tests/test_qml_settings_diagnostic.py -v
"""

from pathlib import Path

from PySide6.QtCore import QObject, QUrl
from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent

QML_DIR = (
    Path(__file__).resolve().parent.parent / "src" / "skill_manager" / "SkillManagerComponents"
)


def _format_errors(errors):
    return "\n".join(f"  - {e.toString()}" for e in errors)


def _load_qml(qapp, qml_path: Path, controller: QObject):
    """Load a QML file with the same setup the real app uses.

    Returns a tuple of (component, object, errors, warnings).

    Uses ``QQmlApplicationEngine`` (matching the real app) because
    ``QQmlEngine`` alone is stricter about the ``data`` list-property
    type of objects added as children — strict enough to reject
    ``QGfxSourceProxy`` inside ``Qt5Compat.GraphicalEffects.ColorOverlay``
    and trigger false-positive errors. The real AppController is required
    because the QML files ``import App 1.0``.
    """
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("appController", controller)
    engine.addImportPath(str(QML_DIR.parent))

    warnings = []
    engine.warnings.connect(lambda msgs: warnings.extend(m.toString() for m in msgs))

    component = QQmlComponent(engine)
    component.setData(
        qml_path.read_text(encoding="utf-8").encode(),
        QUrl.fromLocalFile(str(qml_path)),
    )

    errors = list(component.errors()) if component.isError() else []
    obj = None
    if component.isReady() and not errors:
        obj = component.create()

    return engine, component, obj, errors, warnings


def test_settings_view_loads_without_errors(qapp, app_controller):
    """SettingsView.qml must load cleanly — no compile errors, no missing types.

    Previous failure modes covered here:
      - 'Type GlassPill unavailable' (Qt 6.11 `data` strict-type-check rejects
        `QQuickItem` children; fixed by removing the redundant inner `Item`
        and promoting the `Rectangle` to the root).
      - 'Type SmoothScrollView unavailable' chained through ScrollView /
        ScrollBar (same `data` issue, only triggers under the Windows native
        style — kept covered here as a regression guard).
    """
    path = QML_DIR / "views" / "SettingsView.qml"

    engine, component, obj, errors, warnings = _load_qml(qapp, path, app_controller)

    assert not errors, (
        f"SettingsView.qml failed to load with {len(errors)} error(s):\n"
        f"{_format_errors(errors)}\n\n"
        f"Warnings:\n" + "\n".join(f"  - {w}" for w in warnings)
    )
    assert obj is not None, "SettingsView component.create() returned None"
    assert len(obj.children()) > 0, (
        f"SettingsView root has no children — view will render empty. Warnings: {warnings}"
    )


def test_settings_view_root_has_visible_size(qapp, app_controller):
    """After load, the SettingsView root must have a non-zero size.

    The root `Item` in SettingsView.qml relies on its parent `Loader` to
    set `width`/`height`. This test instantiates the view directly (no
    Loader), so we explicitly resize it. If the view's internal
    ColumnLayout/StackLayout doesn't fill a non-zero parent, the page
    renders empty in the real app.
    """
    path = QML_DIR / "views" / "SettingsView.qml"

    engine, component, obj, errors, warnings = _load_qml(qapp, path, app_controller)
    assert not errors, f"Load errors:\n{_format_errors(errors)}"
    assert obj is not None

    obj.setWidth(800)
    obj.setHeight(600)

    # Walk the tree and report every Item with a non-zero size.
    def walk(item, depth=0):
        for child in item.findChildren(QObject):
            if not hasattr(child, "width"):
                continue
            if child.width() > 0 and child.height() > 0:
                yield depth, child

    visible = list(walk(obj))
    assert visible, (
        f"No visible children found in SettingsView — page will be blank. "
        f"Root size: {obj.width()}x{obj.height()}. "
        f"Children: {[type(c).__name__ + f'({c.width()}x{c.height()})' for c in obj.findChildren(QObject) if hasattr(c, 'width')][:10]}"
    )


def test_settings_view_stacklayout_has_content(qapp, app_controller):
    """The StackLayout inside SettingsView must contain all 3 tab pages.

    SettingsView uses a `settingsTab` int property to drive a StackLayout
    with three children: General (SmoothScrollView), Shortcuts
    (ShortcutsSettings), About (SmoothScrollView). If any of these is
    missing the corresponding tab renders blank.
    """
    path = QML_DIR / "views" / "SettingsView.qml"

    engine, component, obj, errors, warnings = _load_qml(qapp, path, app_controller)
    assert not errors, f"Load errors:\n{_format_errors(errors)}"
    assert obj is not None

    obj.setWidth(800)
    obj.setHeight(600)

    # Find the StackLayout by checking for the `currentIndex` property
    stack = None
    for child in obj.findChildren(QObject):
        if (
            child.metaObject().indexOfProperty("currentIndex") >= 0
            and child.metaObject().indexOfProperty("count") >= 0
        ):
            stack = child
            break

    assert stack is not None, (
        f"StackLayout not found in SettingsView. "
        f"Children with width: {[(type(c).__name__, c.width()) for c in obj.findChildren(QObject) if hasattr(c, 'width')]}"
    )
    count = stack.property("count")
    assert count == 3, (
        f"StackLayout expected 3 children (General, Shortcuts, About), got {count}. "
        f"This means one tab is missing and will render blank."
    )


def test_glass_pill_loads_without_data_property_error(qapp, app_controller):
    """GlassPill must load cleanly — no `data` property strict-type error.

    This guards against the Qt 6.11.1 regression where QQuickItem children
    cannot be added to a `data` list declared as `QObject`. The original
    GlassPill had an empty inner `Item` inside a Rectangle which triggered
    this. Keeping a regression test here so the same bug can't sneak back in.
    """
    path = QML_DIR / "GlassPill.qml"

    engine, component, obj, errors, warnings = _load_qml(qapp, path, app_controller)

    assert not errors, f"GlassPill.qml failed to load:\n{_format_errors(errors)}"
    assert obj is not None
