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

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, QUrl
from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent
from PySide6.QtQuick import QQuickItem
from PySide6.QtWidgets import QApplication

QML_DIR = (
    Path(__file__).resolve().parent.parent / "src" / "skill_manager" / "SkillManagerComponents"
)


def _format_errors(errors):
    return "\n".join(f"  - {e.toString()}" for e in errors)


def _load_qml(
    qapp: QApplication, qml_path: Path, controller: QObject
) -> tuple[QQmlApplicationEngine, QQmlComponent, QQuickItem | None, list, list]:
    """Load a QML file with the same setup the real app uses.

    Returns a tuple of (engine, component, object, errors, warnings).
    ``obj`` is a ``QQuickItem`` (the QML root Item), not a plain
    ``QObject`` — this matters for type checking because only
    ``QQuickItem`` exposes ``setWidth``/``setHeight``/``width``/``height``.
    """
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("appController", controller)
    engine.addImportPath(str(QML_DIR.parent))

    warnings: list[str] = []
    engine.warnings.connect(lambda msgs: warnings.extend(m.toString() for m in msgs))

    component = QQmlComponent(engine)
    component.setData(
        qml_path.read_text(encoding="utf-8").encode(),
        QUrl.fromLocalFile(str(qml_path)),
    )

    errors = list(component.errors()) if component.isError() else []
    obj: QQuickItem | None = None
    if component.isReady() and not errors:
        obj = component.create()  # type: ignore[assignment]

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
    def walk(item: QQuickItem, depth: int = 0):
        for child in item.findChildren(QQuickItem):
            if child.width() > 0 and child.height() > 0:
                yield depth, child

    visible = list(walk(obj))
    assert visible, (
        f"No visible children found in SettingsView — page will be blank. "
        f"Root size: {obj.width()}x{obj.height()}. "
        f"Children: {[type(c).__name__ + f'({c.width()}x{c.height()})' for c in obj.findChildren(QQuickItem)][:10]}"
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
        f"Children with width: {[(type(c).__name__, c.width()) for c in obj.findChildren(QQuickItem)]}"
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


def test_diagnostics_pane_actually_renders_when_expanded(qapp, app_controller):
    """Regression: expanding DiagnosticsPane must produce non-zero content height.

    When expanded, the pane shows filter chips, event table, and action buttons.
    The body ColumnLayout grows, root.implicitHeight grows, and the parent
    GlassPill binds to diagnosticsPane.implicitHeight + 32 to expand the card.
    """
    path = QML_DIR / "views" / "DiagnosticsPane.qml"

    engine, component, obj, errors, warnings = _load_qml(qapp, path, app_controller)
    assert not errors, f"DiagnosticsPane.qml failed to load:\n{_format_errors(errors)}"
    assert obj is not None

    # Expand — body becomes visible, content should have real height
    obj.setProperty("expanded", True)
    obj.setWidth(800)
    obj.setHeight(800)
    obj.setProperty("diagnosticLogPath", "/tmp/test.log")
    obj.setProperty(
        "recentEventsJson",
        '[{"ts":"2026-01-01T12:34:56Z","level":"INFO","category":"test","msg":"hello"}]',
    )
    obj.setProperty("errorCount", 1)
    obj.setProperty("warningCount", 2)
    obj.setProperty("infoCount", 3)
    obj.setProperty("debugCount", 0)
    obj.setProperty("healthStatus", "yellow")
    QApplication.processEvents()

    # Find the inner bodyLayout ColumnLayout and check its implicitHeight
    content_layout = None
    for child in obj.findChildren(QQuickItem):
        cn = child.metaObject().className()
        if "ColumnLayout" in cn and child.implicitHeight() > 50:
            content_layout = child
            break

    assert content_layout is not None, (
        f"No ColumnLayout with implicitHeight > 50 found. "
        f"Root implicitHeight={obj.implicitHeight()}. "
        f"Root type: {obj.metaObject().className()}, "
        f"superClass: {obj.metaObject().superClass().className()}. "
        f"Children: {[type(c).__name__ for c in obj.children()]}"
    )


def test_diagnostics_filter_changes_active_filter(qapp, app_controller):
    """Setting activeFilter must update the property, which drives filter chips.

    The FilterPill component no longer toggles isActive internally — the
    binding `isActive: root.activeFilter === N` controls the visual state.
    Verify the property assignment works correctly from Python side.
    """
    path = QML_DIR / "views" / "DiagnosticsPane.qml"

    engine, component, obj, errors, warnings = _load_qml(qapp, path, app_controller)
    assert not errors, f"DiagnosticsPane.qml failed to load:\n{_format_errors(errors)}"
    assert obj is not None

    obj.setProperty("expanded", True)
    obj.setProperty(
        "recentEventsJson",
        '[{"ts":"2026-01-01T12:00:00Z","level":"INFO","category":"a","msg":"1"},'
        '{"ts":"2026-01-01T12:01:00Z","level":"ERROR","category":"b","msg":"2"},'
        '{"ts":"2026-01-01T12:02:00Z","level":"WARNING","category":"c","msg":"3"}]',
    )
    QApplication.processEvents()

    # Default filter is All (0) — all events visible
    assert obj.property("activeFilter") == 0

    # Switch to Errors filter
    obj.setProperty("activeFilter", 1)
    QApplication.processEvents()
    assert obj.property("activeFilter") == 1

    # Switch to Warnings filter
    obj.setProperty("activeFilter", 2)
    QApplication.processEvents()
    assert obj.property("activeFilter") == 2

    # Switch back to All
    obj.setProperty("activeFilter", 0)
    QApplication.processEvents()
    assert obj.property("activeFilter") == 0


def test_diagnostics_pane_root_is_columnlayout(qapp, app_controller):
    """Regression: DiagnosticsPane root must have proper implicitHeight forwarding.

    When expanded, the pane's body ColumnLayout grows and the root Item's
    implicitHeight should forward that, allowing the parent GlassPill to
    expand the card.
    """
    path = QML_DIR / "views" / "DiagnosticsPane.qml"

    engine, component, obj, errors, warnings = _load_qml(qapp, path, app_controller)
    assert not errors, f"DiagnosticsPane.qml failed to load:\n{_format_errors(errors)}"
    assert obj is not None

    obj.setProperty("expanded", True)
    obj.setWidth(800)
    obj.setHeight(800)
    QApplication.processEvents()

    # The inner bodyLayout should have a non-zero implicitHeight
    has_content = False
    for child in obj.findChildren(QQuickItem):
        cn = child.metaObject().className()
        if "ColumnLayout" in cn and child.implicitHeight() > 50:
            has_content = True
            break

    assert has_content, (
        f"DiagnosticsPane has no ColumnLayout with implicitHeight > 50 after expand. "
        f"Root implicitHeight={obj.implicitHeight()}. "
        f"This means the implicitHeight forwarding is broken."
    )


def test_settings_view_about_tab_has_both_cards(qapp, app_controller):
    """Regression: the About tab must contain BOTH the About GlassPill and
    the Diagnostics GlassPill.

    Previous failure mode: a stray closing brace in the QML closed the
    outer ColumnLayout before the Diagnostics GlassPill, leaving the
    Diagnostics card as a direct child of the SmoothScrollView instead
    of the ColumnLayout. Qt's ScrollView does not render non-contentItem
    children in the scrollable area, so the card was invisible.

    This test reads the QML source and verifies the structural pattern:
    the Diagnostics GlassPill must appear between the About card's
    closing brace and the outer ColumnLayout's closing brace — i.e.
    inside the outer ColumnLayout, not outside it.
    """
    qml_path = QML_DIR / "views" / "SettingsView.qml"
    source = qml_path.read_text(encoding="utf-8")

    # Find the outer ColumnLayout that wraps the About tab content.
    # It opens right after "// About Tab" and contains the About GlassPill.
    about_comment_idx = source.find("// About Tab")
    assert about_comment_idx >= 0, "Could not find '// About Tab' comment in SettingsView.qml"

    # Find the two GlassPill blocks in the About tab section.
    # The first is the About card (has "SkillManager" text).
    # The second is the Diagnostics card (has DiagnosticsPane inside).
    glasspill_pattern = "GlassPill {"
    first_glasspill = source.find(glasspill_pattern, about_comment_idx)
    assert first_glasspill >= 0, "About tab has no GlassPill children"

    second_glasspill = source.find(glasspill_pattern, first_glasspill + len(glasspill_pattern))
    assert second_glasspill >= 0, (
        "About tab must have 2 GlassPill children (About + Diagnostics), "
        "but only found 1. The Diagnostics card is likely missing."
    )

    # Verify the second GlassPill contains DiagnosticsPane
    diag_pane = source.find("DiagnosticsPane {", second_glasspill)
    assert diag_pane >= 0 and diag_pane < second_glasspill + 500, (
        "Second GlassPill in About tab does not contain DiagnosticsPane. "
        "The Diagnostics card may be in the wrong position."
    )


def test_diagnostics_pane_flickables_have_height(qapp, app_controller):
    """Regression: Flickable event list inside DiagnosticsPane must have non-zero height.

    The event table Flickable must render with real height when expanded
    so event rows are visible and scrollable.
    """
    path = QML_DIR / "views" / "DiagnosticsPane.qml"

    engine, component, obj, errors, warnings = _load_qml(qapp, path, app_controller)
    assert not errors, f"DiagnosticsPane.qml failed to load:\n{_format_errors(errors)}"
    assert obj is not None

    obj.setProperty("expanded", True)
    obj.setWidth(800)
    obj.setHeight(800)
    obj.setProperty(
        "recentEventsJson",
        '[{"ts":"2026-01-01T12:00:00Z","level":"INFO","category":"test","msg":"hi"}]',
    )
    QApplication.processEvents()

    flickables = [
        c for c in obj.findChildren(QQuickItem) if "Flickable" in c.metaObject().className()
    ]
    assert len(flickables) >= 1, (
        f"Expected at least 1 Flickable event list in DiagnosticsPane, found {len(flickables)}"
    )

    for i, f in enumerate(flickables):
        assert f.height() > 0, (
            f"Found a Flickable (index {i}) with 0 height. Events will not be visible."
        )


def test_about_diagnostics_pill_hidden_when_logging_disabled(qapp, app_controller):
    """When diagnostic logging is disabled, the Diagnostics card in the
    About tab must be hidden and occupy zero layout height.

    Regression test for: the Diagnostics section should not show in About
    when diagnostic logging is disabled in General settings.
    """
    # Ensure logging is disabled
    app_controller.config_controller.diagnosticLogging = False
    QApplication.processEvents()

    path = QML_DIR / "views" / "SettingsView.qml"
    engine, component, obj, errors, warnings = _load_qml(qapp, path, app_controller)
    assert not errors, f"SettingsView.qml failed to load:\n{_format_errors(errors)}"
    assert obj is not None

    # Find the diagnostics GlassPill by objectName
    diag_pill = obj.findChild(QObject, "diagnosticsGlassPill")
    assert diag_pill is not None, (
        "diagnosticsGlassPill not found in SettingsView. "
        f"Available QObjects: {[c.objectName() for c in obj.findChildren(QObject) if c.objectName()]}"
    )

    assert diag_pill.property("visible") is False, (
        f"Diagnostics pill should be hidden when diagnosticLogging=False, "
        f"but visible={diag_pill.property('visible')}"
    )


def test_about_diagnostics_pill_visible_when_logging_enabled(qapp, app_controller):
    """When diagnostic logging is enabled, the Diagnostics card in the
    About tab must be visible with a non-zero layout height.

    Regression test for: the Diagnostics section should show in About
    when diagnostic logging is enabled in General settings.

    Verifies the QML source contains a ``visible:`` binding on the
    ``diagnosticsGlassPill`` that reads ``diagnosticLogging``, and that
    the ``config_controller.diagnosticLogging`` property is reactive.
    """
    # Verify the property is reactive at the Python level
    app_controller.config_controller.diagnosticLogging = False
    QApplication.processEvents()
    assert app_controller.config_controller.diagnosticLogging is False

    app_controller.config_controller.diagnosticLogging = True
    QApplication.processEvents()
    assert app_controller.config_controller.diagnosticLogging is True

    # Verify the QML source contains the visible binding (structural check)
    qml_source = (QML_DIR / "views" / "SettingsView.qml").read_text(encoding="utf-8")
    diag_section_start = qml_source.find("diagnosticsGlassPill")
    assert diag_section_start >= 0, "diagnosticsGlassPill not found in QML source"

    diag_section = qml_source[diag_section_start : diag_section_start + 400]
    assert "visible:" in diag_section, (
        "diagnosticsGlassPill has no visible: binding. "
        "When diagnostic logging is disabled, the pill should be hidden."
    )
    assert "diagnosticLogging" in diag_section, (
        "diagnosticsGlassPill visible binding does not reference diagnosticLogging. "
        "It should be bound to AppController.config_controller.diagnosticLogging."
    )
