import re
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


def test_qml_buttons_route_through_shared_primitives():
    allowed_raw_button_files = {
        "ActionButton.qml",
        "FilterPill.qml",
        "GlassToggleButton.qml",
        "IconButton.qml",
        "SidebarButton.qml",
        "TopBarButton.qml",
    }

    offenders = []
    for path in QML_DIR.rglob("*.qml"):
        text = path.read_text(encoding="utf-8")
        if re.search(r"(^|\s)Button\s*\{", text) and path.name not in allowed_raw_button_files:
            offenders.append(str(path.relative_to(QML_DIR)))

    assert offenders == []
    assert "IconButton 1.0 IconButton.qml" in (QML_DIR / "qmldir").read_text(encoding="utf-8")


def test_shared_buttons_center_content_and_use_role_tokens():
    action_button = (QML_DIR / "ActionButton.qml").read_text(encoding="utf-8")
    icon_button = (QML_DIR / "IconButton.qml").read_text(encoding="utf-8")
    toggle = (QML_DIR / "GlassToggleButton.qml").read_text(encoding="utf-8")
    sidebar = (QML_DIR / "SidebarButton.qml").read_text(encoding="utf-8")
    topbar = (QML_DIR / "TopBarButton.qml").read_text(encoding="utf-8")

    for source in (action_button, icon_button, toggle, topbar):
        assert "anchors.centerIn: parent" in source

    assert "anchors.leftMargin: 12" in sidebar
    assert 'property string role: "secondary"' in icon_button
    assert 'control.role === "destructive"' in icon_button
    assert 'control.role === "primary"' in action_button
    assert "Theme.disabledControl" in icon_button
    assert "Theme.dangerHover" in icon_button


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


def test_skill_rows_use_cached_model_grouping_for_smooth_collapse():
    skill_item = (QML_DIR / "SkillItem.qml").read_text(encoding="utf-8")
    models_py = (QML_DIR.parent / "core" / "models.py").read_text(encoding="utf-8")

    assert "model.isFirstInSubcategory" in skill_item
    assert "model.isMainCollapsed" in skill_item
    assert "model.isSubCollapsed" in skill_item
    assert "get_skill_at(index - 1)" not in skill_item
    assert "Behavior on height" not in skill_item
    assert "IsFirstInSubcategoryRole" in models_py
    assert "_build_visible_rows" in models_py


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


def test_library_and_quick_copy_filters_are_view_scoped():
    quick_copy = (QML_DIR / "views" / "QuickCopyView.qml").read_text(encoding="utf-8")
    library = (QML_DIR / "views" / "LibraryView.qml").read_text(encoding="utf-8")

    assert "AppController.libraryModel" in library
    assert "AppController.quickCopyModel" not in library
    assert "projectFilter" not in library
    assert 'setViewFilterForView("Library"' in library

    assert "AppController.quickCopyModel" in quick_copy
    assert 'setViewFilterForView("QuickCopy"' in quick_copy


def test_folder_picker_native_uses_qt6_properties():
    folder_picker = (QML_DIR / "dialogs" / "FolderPickerNative.qml").read_text(encoding="utf-8")
    assert "folder.toString()" not in folder_picker
    assert "selectedFolder.toString()" in folder_picker

