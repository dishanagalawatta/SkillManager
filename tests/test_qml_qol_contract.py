from pathlib import Path

QML_DIR = (
    Path(__file__).resolve().parent.parent / "src" / "skill_manager" / "SkillManagerComponents"
)


def test_quick_copy_and_library_do_not_use_bottom_status_bars():
    quick_copy = (QML_DIR / "views" / "QuickCopyView.qml").read_text(encoding="utf-8")
    library = (QML_DIR / "views" / "LibraryView.qml").read_text(encoding="utf-8")
    qmldir = (QML_DIR / "qmldir").read_text(encoding="utf-8")

    assert 'objectName: "quickCopyStatusBar"' not in quick_copy
    assert 'objectName: "libraryStatusBar"' not in library
    assert "ViewStatusBar" not in quick_copy
    assert "ViewStatusBar" not in library
    assert "ViewStatusBar" not in qmldir


def test_top_status_area_is_the_only_routine_status_surface():
    top_bar = (QML_DIR / "TopBar.qml").read_text(encoding="utf-8")
    updates = (QML_DIR / "views" / "UpdatesView.qml").read_text(encoding="utf-8")

    assert 'objectName: "topStatusPill"' in top_bar
    assert 'objectName: "topStatusText"' in top_bar
    assert "AppController.statusMessage" in top_bar
    assert "AppController.statusMessage" not in updates
    assert 'text: "Status:"' not in updates


def test_skill_rows_are_selection_first_in_main_views():
    quick_copy = (QML_DIR / "views" / "QuickCopyView.qml").read_text(encoding="utf-8")
    library = (QML_DIR / "views" / "LibraryView.qml").read_text(encoding="utf-8")
    skill_item = (QML_DIR / "SkillItem.qml").read_text(encoding="utf-8")

    assert "property bool showInlineDelete: true" in skill_item
    assert "visible: root.showInlineDelete && mouseArea.containsMouse" in skill_item
    assert "showInlineDelete: false" in quick_copy
    assert "showInlineDelete: false" in library


def test_action_bars_use_shared_action_buttons_and_keep_primary_names():
    quick_copy = (QML_DIR / "views" / "QuickCopyView.qml").read_text(encoding="utf-8")
    library = (QML_DIR / "views" / "LibraryView.qml").read_text(encoding="utf-8")
    updates = (QML_DIR / "views" / "UpdatesView.qml").read_text(encoding="utf-8")
    qmldir = (QML_DIR / "qmldir").read_text(encoding="utf-8")

    assert "ActionButton 1.0 ActionButton.qml" in qmldir
    assert quick_copy.count("ActionButton {") >= 5
    assert library.count("ActionButton {") >= 5
    assert updates.count("ActionButton {") >= 2
    assert 'objectName: "copySelectedBtn"' in quick_copy
    assert 'objectName: "quickCopyDeleteSelectedBtn"' in quick_copy
    assert 'objectName: "quickCopyDestructiveDivider"' in quick_copy
    assert 'objectName: "libraryDestructiveDivider"' in library
    assert 'labelText: "Copy Selected"' in quick_copy
    assert 'labelText: "Copy to Project"' in library
    assert 'labelText: "Scan"' in updates
    assert 'labelText: "Update All"' in updates


def test_compact_rows_are_persisted_and_wired_to_skill_items():
    settings = (QML_DIR / "views" / "SettingsView.qml").read_text(encoding="utf-8")
    skill_item = (QML_DIR / "SkillItem.qml").read_text(encoding="utf-8")
    app_py = (QML_DIR.parent / "app.py").read_text(encoding="utf-8")

    assert "Compact List Rows" in settings
    assert "AppController.compactListRows" in settings
    assert "AppController.setCompactListRows(checked)" in settings
    assert "property bool compactRows: AppController.compactListRows" in skill_item
    assert "_compact_list_rows" in app_py


def test_raw_skill_rows_show_name_only_and_use_tighter_heights():
    skill_item = (QML_DIR / "SkillItem.qml").read_text(encoding="utf-8")
    quick_copy = (QML_DIR / "views" / "QuickCopyView.qml").read_text(encoding="utf-8")
    library = (QML_DIR / "views" / "LibraryView.qml").read_text(encoding="utf-8")

    assert 'text: model ? model.name : ""' in skill_item
    assert 'model.project + " • " + model.category' not in skill_item
    assert "root.compactRows ? 42 : 54" in skill_item
    assert "delegate: SkillItem" in quick_copy
    assert "delegate: SkillItem" in library


def test_dark_polish_tokens_drive_shared_components():
    theme = (QML_DIR / "Theme.qml").read_text(encoding="utf-8")
    action_button = (QML_DIR / "ActionButton.qml").read_text(encoding="utf-8")
    skill_item = (QML_DIR / "SkillItem.qml").read_text(encoding="utf-8")
    toggle = (QML_DIR / "GlassToggleButton.qml").read_text(encoding="utf-8")
    top_bar = (QML_DIR / "TopBar.qml").read_text(encoding="utf-8")

    for token in (
        "disabledControl",
        "selectedRow",
        "selectedRowHover",
        "selectedRowBorder",
        "dangerHover",
    ):
        assert token in theme

    assert "Theme.disabledControl" in action_button
    assert "Theme.dangerHover" in action_button
    assert "Accessible.description: tooltipText" in action_button
    assert "HoverHandler" in action_button
    assert "Theme.selectedRow" in skill_item
    assert "Theme.selectedRowHover" in skill_item
    assert "Theme.selectedRowBorder" in skill_item
    assert "Theme.selectedRow" in toggle
    assert "Accessible.description: tooltipText" in toggle
    assert "color: Theme.label" in top_bar


def test_quick_copy_project_dropdown_uses_labels():
    quick_copy = (QML_DIR / "views" / "QuickCopyView.qml").read_text(encoding="utf-8")
    # Must use AppController.projectLabels, not AppController.projects
    assert "AppController.projectLabels" in quick_copy
    assert "AppController.projects" not in quick_copy
