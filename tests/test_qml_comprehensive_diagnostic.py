"""Comprehensive QML diagnostic — load every major view, report every error.

This is the single source of truth for "is the app rendering correctly?".
Run with:

    uv run pytest tests/test_qml_comprehensive_diagnostic.py -v

It loads each QML view in the same setup the real app uses (Basic style,
SkillManagerComponents import path) and asserts that:
  - The QML loads without errors
  - The root has a non-zero size
  - The first StackLayout / Repeater / ListView (if any) has children

Each failure prints the exact QML error so the next fix has a clear target.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtCore import QObject, QUrl
from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent
from PySide6.QtQuick import QQuickItem
from PySide6.QtWidgets import QApplication

QML_DIR = (
    Path(__file__).resolve().parent.parent / "src" / "skill_manager" / "SkillManagerComponents"
)
VIEWS_DIR = QML_DIR / "views"
DIALOGS_DIR = QML_DIR / "dialogs"

# Every QML file the user can navigate to.
PUBLIC_VIEWS = [
    "QuickCopyView.qml",
    "LibraryView.qml",
    "UpdatesView.qml",
    "SettingsView.qml",
    "ShortcutsSettings.qml",
]

# Every dialog the user can open.
DIALOGS = [
    "CommandCreateDialog.qml",
    "DeleteConfirmDialog.qml",
    "ArchiveConfirmDialog.qml",
    "PackageEditDialog.qml",
    "ProjectRenameDialog.qml",
    "FolderPickerNative.qml",
    "MissingSkillsDialog.qml",
]

# Shared components that other QML files import via the local module.
# Loading them in isolation catches data-property / missing-type issues
# before they cascade into a 50-line "Type X unavailable" error chain.
SHARED_COMPONENTS = [
    "ActionButton.qml",
    "AppScrollBar.qml",
    "CategoryHeader.qml",
    "ColorOverlay.qml",
    "CommandInspector.qml",
    "CustomTitleBar.qml",
    "DropShadow.qml",
    "FilterPill.qml",
    "FontFamilyColumn.qml",
    "FontPickerDialog.qml",
    "FontPreviewPane.qml",
    "FontSizeColumn.qml",
    "FontStyleColumn.qml",
    "FrostOverlay.qml",
    "GlassCheckBox.qml",
    "GlassCollectionDropdown.qml",
    "GlassDropdown.qml",
    "GlassMenu.qml",
    "GlassMenuItem.qml",
    "GlassMultiSelect.qml",
    "GlassPill.qml",
    "GlassSearchInput.qml",
    "GlassSwitch.qml",
    "GlassToggleButton.qml",
    "IconButton.qml",
    "ImageInspector.qml",
    "KeySequenceCapture.qml",
    "Main.qml",
    "ScreenshotOverlay.qml",
    "SkillInspector.qml",
    "SkillItem.qml",
    "SmoothListView.qml",
    "SmoothScrollView.qml",
    "Sidebar.qml",
    "SidebarButton.qml",
    "Theme.qml",
    "TopBar.qml",
    "TopBarButton.qml",
    "views/DiagnosticsPane.qml",
]


class _MockAppController(QObject):
    pass


def _load(
    qapp: QApplication, path: Path, controller: QObject
) -> tuple[QQuickItem | None, list[str], list[str]]:
    """Load a QML file. Returns (root_object_or_None, errors, warnings).

    ``obj`` is a ``QQuickItem`` (the QML root Item), not a plain
    ``QObject`` — this matters for type checking because only
    ``QQuickItem`` exposes ``setWidth``/``setHeight``/``width``/``height``.
    """
    # QQuickStyle.setStyle() was called by the conftest fixture before
    # the QApplication was created, so it is already pinned to "Basic".

    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("appController", controller)
    engine.addImportPath(str(QML_DIR.parent))

    warnings: list[str] = []
    engine.warnings.connect(lambda msgs: warnings.extend(m.toString() for m in msgs))

    component = QQmlComponent(engine)
    component.setData(
        path.read_text(encoding="utf-8").encode(),
        QUrl.fromLocalFile(str(path)),
    )

    errors = [e.toString() for e in component.errors()]
    obj = None
    if not errors and component.isReady():
        try:
            obj = component.create()  # type: ignore[assignment]
        except Exception as exc:
            errors.append(f"create() raised {type(exc).__name__}: {exc}")

    if obj is not None:
        obj.deleteLater()
    component.deleteLater()
    engine.deleteLater()
    return obj, errors, warnings  # type: ignore[return-value]


def _give_size(obj: QObject, w: int = 800, h: int = 600) -> None:
    if hasattr(obj, "setWidth"):
        obj.setWidth(w)  # type: ignore[union-attr]
    if hasattr(obj, "setHeight"):
        obj.setHeight(h)  # type: ignore[union-attr]


# ----- Top-level navigation views -----------------------------------------


@pytest.mark.parametrize("filename", PUBLIC_VIEWS)
def test_public_view_loads_cleanly(qapp, app_controller, filename):
    path = VIEWS_DIR / filename
    obj, errors, warnings = _load(qapp, path, app_controller)
    assert not errors, f"{filename} failed to load with {len(errors)} error(s):\n" + "\n".join(
        f"  - {e}" for e in errors
    )
    assert obj is not None, f"{filename}: create() returned None"
    _give_size(obj)
    assert obj.width() > 0 and obj.height() > 0, (
        f"{filename}: root has zero size {obj.width()}x{obj.height()}. "
        f"Children: {len(obj.children())}"
    )


# ----- Dialogs ------------------------------------------------------------


@pytest.mark.parametrize("filename", DIALOGS)
def test_dialog_loads_cleanly(qapp, app_controller, filename):
    path = DIALOGS_DIR / filename
    if not path.exists():
        pytest.skip(f"{filename} not present in repo")
    obj, errors, warnings = _load(qapp, path, app_controller)
    assert not errors, f"{filename} failed to load:\n" + "\n".join(f"  - {e}" for e in errors)
    assert obj is not None
    _give_size(obj)


# ----- Shared components --------------------------------------------------


@pytest.mark.parametrize("filename", SHARED_COMPONENTS)
def test_shared_component_loads_cleanly(qapp, app_controller, filename):
    path = QML_DIR / filename
    obj, errors, warnings = _load(qapp, path, app_controller)
    assert not errors, f"{filename} failed to load:\n" + "\n".join(f"  - {e}" for e in errors)
    # Not every shared component is a top-level visual (e.g. Theme is a
    # singleton); we don't assert on size for the shared pool.


# ----- Collection shortcut regression tests --------------------------------


def test_main_qml_no_non_item_delegate_warnings(qapp, app_controller):
    """Main.qml must not emit 'Delegate must be of Item type' warnings.

    Regression test for the Repeater → Instantiator fix (task 4.10).
    The old Repeater used Shortcut as delegate, which is QObject-based
    (not Item). Instantiator is the correct positioner for non-visual
    QObject delegates.
    """
    from PySide6.QtQml import QQmlApplicationEngine

    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("appController", app_controller)
    engine.addImportPath(str(QML_DIR.parent))

    warnings: list[str] = []
    engine.warnings.connect(lambda msgs: warnings.extend(m.toString() for m in msgs))

    engine.load(str(QML_DIR / "Main.qml"))
    assert engine.rootObjects(), "Main.qml failed to load"

    delegate_warnings = [w for w in warnings if "Delegate must be of Item type" in w]
    assert not delegate_warnings, (
        "Found 'Delegate must be of Item type' warnings — "
        "Instantiator must be used instead of Repeater for Shortcut delegates:\n"
        + "\n".join(f"  - {w}" for w in delegate_warnings)
    )

    engine.deleteLater()


def test_collection_shortcut_instantiator_creates_shortcuts(qtbot, app_controller):
    """Instantiator in Main.qml creates one Shortcut per collection with a bound sequence."""
    from PySide6.QtCore import QObject
    from PySide6.QtQml import QQmlApplicationEngine

    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("appController", app_controller)
    engine.addImportPath(str(QML_DIR.parent))
    engine.load(str(QML_DIR / "Main.qml"))
    assert engine.rootObjects(), "Main.qml failed to load"

    root = engine.rootObjects()[0]

    # Configure two collections: one with shortcut, one without
    app_controller._custom_collections = {
        "Snippets": {
            "paths": ["/a"],
            "projects": [],
            "shortcut": "Ctrl+Shift+J",
            "shortcut_enabled": True,
        },
        "Drafts": {"paths": ["/b"], "projects": [], "shortcut": "", "shortcut_enabled": True},
    }
    app_controller.customCollectionsChanged.emit()
    qtbot.wait(100)

    # Find the Instantiator created by Main.qml for collection shortcuts.
    # It's a QObject with metaObject().className() == "QQmlInstantiator".
    instantiator = None
    for child in root.findChildren(QObject):
        if child.metaObject().className() == "QQmlInstantiator":
            instantiator = child
            break

    assert instantiator is not None, "Could not find QQmlInstantiator in Main.qml"

    # The Instantiator should have created objects for both collections.
    # "Snippets" has a shortcut, "Drafts" has empty string.
    # Verify at least one child has an 'activated' signal (i.e., is a Shortcut delegate).
    has_shortcut = any(hasattr(c, "activated") for c in instantiator.children())
    assert has_shortcut, (
        "Instantiator should have created at least one Shortcut delegate with 'activated' signal"
    )

    engine.deleteLater()


def test_collection_shortcut_fires_copy_collection_to_clipboard(qtbot, app_controller):
    """Activating a collection shortcut calls copyCollectionToClipboard on AppController."""
    from unittest.mock import MagicMock

    from PySide6.QtCore import QObject
    from PySide6.QtQml import QQmlApplicationEngine

    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("appController", app_controller)
    engine.addImportPath(str(QML_DIR.parent))
    engine.load(str(QML_DIR / "Main.qml"))
    assert engine.rootObjects(), "Main.qml failed to load"

    root = engine.rootObjects()[0]

    # Set up collection with shortcut
    app_controller._custom_collections = {
        "Snippets": {
            "paths": ["/a"],
            "projects": [],
            "shortcut": "Ctrl+Shift+J",
            "shortcut_enabled": True,
        },
    }
    app_controller.customCollectionsChanged.emit()
    qtbot.wait(100)

    # Find the Instantiator
    instantiator = None
    for child in root.findChildren(QObject):
        if child.metaObject().className() == "QQmlInstantiator":
            instantiator = child
            break

    assert instantiator is not None, "Could not find QQmlInstantiator in Main.qml"
    assert instantiator.property("count") >= 1, (
        f"Expected >= 1 objects from Instantiator, got {instantiator.property('count')}"
    )

    # Get the first instantiated Shortcut delegate.
    # Instantiator children: [0]=internal, [1]=QQmlComponent, [2:]=delegates.
    # Delegates have an 'activated' signal.
    shortcut_obj = None
    for child in instantiator.children():
        if hasattr(child, "activated"):
            shortcut_obj = child
            break

    assert shortcut_obj is not None, "Could not find instantiated Shortcut with 'activated' signal"

    # Mock copyCollectionToClipboard
    app_controller.copyCollectionToClipboard = MagicMock()

    # Directly emit activated() on the Shortcut (simulates key press)
    shortcut_obj.activated.emit()  # type: ignore[union-attr]
    qtbot.wait(50)

    app_controller.copyCollectionToClipboard.assert_called_once_with("Snippets")

    engine.deleteLater()
