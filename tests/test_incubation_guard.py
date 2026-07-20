"""Faithful verification of the incubation-cacheBuffer guard.

The harness never hits the ``incubating=True`` branch (test mode forces the
property to ``False``), so the previous "Object or context destroyed during
incubation" fix was unverified. This test drives the guard directly: it loads
the real QML views against the real ``app_controller`` fixture, pokes
``_incubating`` to ``True`` (bypassing the test-mode setter), fires the model
signals that used to race the live delegates, and asserts ``cacheBuffer`` is
deferred (stays 0) instead of being restored mid-incubation; then it ends the
incubation and asserts the deferred restore fires.
"""

from pathlib import Path

import pytest
from PySide6.QtCore import QObject, QUrl
from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent, QQmlProperty

from skill_manager.controllers.font_database_bridge import FontDatabaseBridge

PROJECT_ROOT = Path(__file__).parent.parent
QML_DIR = PROJECT_ROOT / "src" / "skill_manager" / "SkillManagerComponents"

# (qml file, model attribute on app_controller, list objectName)
VIEWS = [
    ("views/QuickCopyView.qml", "_quick_copy_model", "quickCopyList"),
    ("views/LibraryView.qml", "_library_model", "libraryList"),
]


def _read_cache_buffer(lv):
    """Read the ``cacheBuffer`` Qt property without relying on a Python attr."""
    return QQmlProperty.read(lv, "cacheBuffer")


def _find_list_view(root, object_name):
    if object_name:
        lv = root.findChild(QObject, object_name)
        if lv is not None:
            return lv
    # Fallback: the main list is the only QQuickListView in the view.
    for child in root.findChildren(QObject):
        if child.metaObject().className() == "QQuickListView":
            return child
    raise AssertionError("could not locate the ListView in the view")


def _load(qml_path, controller):
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("appController", controller)
    font_bridge = FontDatabaseBridge()
    engine.rootContext().setContextProperty("fontDB", font_bridge)
    engine._font_bridge = font_bridge  # pyright: ignore[reportAttributeAccessIssue]
    engine.addImportPath(str(QML_DIR.parent))
    comp = QQmlComponent(engine)
    comp.setData(
        qml_path.read_text(encoding="utf-8").encode(),
        QUrl.fromLocalFile(str(qml_path)),
    )
    obj = comp.create()
    return engine, comp, obj


@pytest.mark.parametrize("qml_file,model_attr,list_name", VIEWS)
def test_incubation_defers_cachebuffer_restore(
    qml_file, model_attr, list_name, app_controller, qapp
):
    qml_path = QML_DIR / qml_file
    engine, comp, root = _load(qml_path, app_controller)

    errors = [e.toString() for e in comp.errors()]
    assert root is not None, f"failed to load {qml_file}: {errors}"

    model = getattr(app_controller, model_attr)
    lv = _find_list_view(root, list_name)

    # Initial state: Component.onCompleted restored the buffer.
    assert _read_cache_buffer(lv) > 0, "cacheBuffer not initialised by Component.onCompleted"

    try:
        # Enter incubation by poking the private flag (test-mode setter forces False).
        model._incubating = True
        model.incubatingChanged.emit()
        qapp.processEvents()

        # layoutAboutToBeChanged zeroes the buffer; layoutChanged must NOT
        # restore it while incubating (this is the original crash path).
        model.layoutAboutToBeChanged.emit()
        model.layoutChanged.emit()
        qapp.processEvents()
        assert _read_cache_buffer(lv) == 0, "cacheBuffer restored mid-incubation (layoutChanged)"

        # modelReset path must also defer.
        model.modelAboutToBeReset.emit()
        model.modelReset.emit()
        qapp.processEvents()
        assert _read_cache_buffer(lv) == 0, "cacheBuffer restored mid-incubation (modelReset)"

        # structureMutated path must also defer.
        model.aboutToMutateStructure.emit()
        model.structureMutated.emit()
        qapp.processEvents()
        assert _read_cache_buffer(lv) == 0, "cacheBuffer restored mid-incubation (structureMutated)"

        # End incubation: onIncubatingChanged must replay + restore the buffer.
        model._incubating = False
        model.incubatingChanged.emit()
        qapp.processEvents()
        assert _read_cache_buffer(lv) > 0, "cacheBuffer not restored after incubation ended"
    finally:
        # Restore clean state for sibling tests sharing the session controller.
        model._incubating = False
        qapp.processEvents()
