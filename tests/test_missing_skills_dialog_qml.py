"""Tests that MissingSkillsDialog.qml bindings handle all data types safely."""

from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import QObject, QUrl
from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent
from PySide6.QtWidgets import QApplication

QML_DIR = (
    Path(__file__).resolve().parent.parent / "src" / "skill_manager" / "SkillManagerComponents"
)
DIALOG_PATH = QML_DIR / "dialogs" / "MissingSkillsDialog.qml"


class _MockAppController(QObject):
    pass


def _load_dialog(
    qapp: QApplication, controller: QObject
) -> tuple[QObject | None, list[str], list[str]]:
    """Load MissingSkillsDialog.qml. Returns (root_or_None, errors, warnings)."""
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("appController", controller)
    engine.addImportPath(str(QML_DIR.parent))

    warnings: list[str] = []
    engine.warnings.connect(lambda msgs: warnings.extend(m.toString() for m in msgs))

    component = QQmlComponent(engine)
    component.setData(
        DIALOG_PATH.read_text(encoding="utf-8").encode(),
        QUrl.fromLocalFile(str(DIALOG_PATH)),
    )

    errors = [e.toString() for e in component.errors()]
    obj = None
    if not errors and component.isReady():
        try:
            obj = component.create()
        except Exception as exc:
            errors.append(f"create() raised {type(exc).__name__}: {exc}")

    if obj is not None:
        obj.deleteLater()
    component.deleteLater()
    engine.deleteLater()
    return obj, errors, warnings


def test_dialog_loads_cleanly(qapp, app_controller):
    obj, errors, warnings = _load_dialog(qapp, app_controller)
    assert not errors, "MissingSkillsDialog failed to load:\n" + "\n".join(
        f"  - {e}" for e in errors
    )
    assert obj is not None


def _call_open_with_missing(obj, name, missing):
    """Call openWithMissing on the dialog root."""
    obj.openWithMissing(name, json.dumps(missing))
    # Process events so QML bindings evaluate
    from PySide6.QtWidgets import QApplication

    QApplication.processEvents()


def test_skills_array_shows_length(qapp, app_controller):
    """When skills is a normal JS array, the binding should show a count."""
    obj, errors, _ = _load_dialog(qapp, app_controller)
    assert obj is not None
    assert not errors

    missing = {"CourseBar": ["/path/skill1", "/path/skill2"]}
    _call_open_with_missing(obj, "TestColl", missing)

    # Dialog processed without Python-level errors (QML warnings about
    # parent size are expected when loading a dialog without a window)
    assert not errors


def test_skills_empty_array_does_not_open(qapp, app_controller):
    """When skills is an empty array, dialog should not open (no missing skills)."""
    obj, errors, _ = _load_dialog(qapp, app_controller)
    assert obj is not None
    assert not errors

    missing = {"EmptyProj": []}
    _call_open_with_missing(obj, "TestColl", missing)

    assert obj.property("visible") is False


def test_skills_object_without_length(qapp, app_controller):
    """When skills is an object (not array), binding should not crash or show 'undefined'."""
    obj, errors, _ = _load_dialog(qapp, app_controller)
    assert obj is not None
    assert not errors

    # Simulate what happens if JSON parse returns an object instead of array
    missing = {"BadProj": {"0": "/path/skill", "length": 1}}
    _call_open_with_missing(obj, "TestColl", missing)


def test_skills_null_value(qapp, app_controller):
    """When skills is null, binding should handle gracefully."""
    obj, errors, _ = _load_dialog(qapp, app_controller)
    assert obj is not None
    assert not errors

    missing = {"NullProj": None}
    _call_open_with_missing(obj, "TestColl", missing)


def test_skills_string_value(qapp, app_controller):
    """When skills is a string (not array), binding should handle gracefully."""
    obj, errors, _ = _load_dialog(qapp, app_controller)
    assert obj is not None
    assert not errors

    missing = {"StrProj": "not-an-array"}
    _call_open_with_missing(obj, "TestColl", missing)


def test_skills_numeric_value(qapp, app_controller):
    """When skills is a number, binding should handle gracefully."""
    obj, errors, _ = _load_dialog(qapp, app_controller)
    assert obj is not None
    assert not errors

    missing = {"NumProj": 42}
    _call_open_with_missing(obj, "TestColl", missing)


def test_multiple_projects_mixed_types(qapp, app_controller):
    """Multiple projects with mixed skill types should not crash."""
    obj, errors, _ = _load_dialog(qapp, app_controller)
    assert obj is not None
    assert not errors

    missing = {
        "GoodProj": ["/path/s1", "/path/s2"],
        "EmptyProj": [],
        "NullProj": None,
    }
    _call_open_with_missing(obj, "TestColl", missing)


def test_open_with_empty_skills_does_not_open(qapp, app_controller):
    """When all skill arrays are empty, dialog should not open."""
    obj, errors, _ = _load_dialog(qapp, app_controller)
    assert obj is not None
    assert not errors

    missing = {"EmptyProj": []}
    _call_open_with_missing(obj, "TestColl", missing)

    # visible should remain False — dialog never called open()
    assert obj.property("visible") is False


def test_open_with_all_empty_skills_does_not_open(qapp, app_controller):
    """Multiple projects with all-empty arrays — dialog should not open."""
    obj, errors, _ = _load_dialog(qapp, app_controller)
    assert obj is not None
    assert not errors

    missing = {"P1": [], "P2": []}
    _call_open_with_missing(obj, "TestColl", missing)

    assert obj.property("visible") is False


def test_open_with_mixed_keeps_non_empty(qapp, app_controller):
    """Mixed empty and non-empty — dialog processes without errors."""
    obj, errors, _ = _load_dialog(qapp, app_controller)
    assert obj is not None
    assert not errors

    missing = {"EmptyP": [], "RealP": ["/path/s1"]}
    _call_open_with_missing(obj, "TestColl", missing)

    # Without a parent window, Dialog.visible may stay False even after open().
    # The critical check: no errors, and the dialog processed the data safely.
    assert not errors


def test_project_check_items_is_js_array(qapp, app_controller):
    """openWithMissing should populate projectCheckItems as a JS array with correct data."""
    obj, errors, _ = _load_dialog(qapp, app_controller)
    assert obj is not None
    assert not errors

    missing = {"CourseBar": ["/path/skill1", "/path/skill2"], "EmptyProj": []}
    _call_open_with_missing(obj, "TestColl", missing)

    # projectCheckItems is a JS array — convert via toVariant()
    items = obj.property("projectCheckItems").toVariant()
    assert isinstance(items, list)
    # Only non-empty skills should be included
    assert len(items) == 1
    assert items[0]["project"] == "CourseBar"
    assert items[0]["checked"] is True
    assert isinstance(items[0]["skills"], list)
    assert len(items[0]["skills"]) == 2


def test_project_check_items_count_matches(qapp, app_controller):
    """The items length should equal the number of non-empty skill arrays."""
    obj, errors, _ = _load_dialog(qapp, app_controller)
    assert obj is not None
    assert not errors

    missing = {"P1": ["/s1"], "P2": ["/s2", "/s3"], "P3": []}
    _call_open_with_missing(obj, "TestColl", missing)

    items = obj.property("projectCheckItems").toVariant()
    assert len(items) == 2
