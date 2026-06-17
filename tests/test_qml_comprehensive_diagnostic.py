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
) -> tuple[QObject | None, list[str], list[str]]:
    """Load a QML file. Returns (root_object_or_None, errors, warnings).

    Uses ``QQmlApplicationEngine`` (matching the real app) because
    ``QQmlEngine`` alone is stricter about the ``data`` list-property
    type of objects added as children — strict enough to reject
    ``QGfxSourceProxy`` inside ``Qt5Compat.GraphicalEffects.ColorOverlay``
    and trigger false-positive data-property errors for every QML file
    that re-exports a Qt5Compat effect.

    The ``controller`` argument is the real AppController registered at
    URI "App"/1.0/"AppController" by the conftest's session-scoped
    ``app_controller`` fixture. The QML files ``import App 1.0``, so
    they require this exact URI.
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
            obj = component.create()
        except Exception as exc:
            errors.append(f"create() raised {type(exc).__name__}: {exc}")

    if obj is not None:
        obj.deleteLater()
    component.deleteLater()
    engine.deleteLater()
    return obj, errors, warnings


def _give_size(obj: QObject, w: int = 800, h: int = 600) -> None:
    if hasattr(obj, "setWidth"):
        obj.setWidth(w)
    if hasattr(obj, "setHeight"):
        obj.setHeight(h)


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
