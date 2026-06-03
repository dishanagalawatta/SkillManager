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
    ui_controller_py = (QML_DIR.parent / "controllers" / "ui_controller.py").read_text(encoding="utf-8")

    assert "Compact List Rows" in settings
    assert "AppController.ui_controller.compactListRows" in settings
    assert "AppController.ui_controller.setCompactListRows(checked)" in settings
    assert "property bool compactRows: AppController.ui_controller.compactListRows" in skill_item
    assert "_compact_list_rows" in ui_controller_py


def test_raw_skill_rows_show_name_only_and_use_tighter_heights():
    skill_item = (QML_DIR / "SkillItem.qml").read_text(encoding="utf-8")
    quick_copy = (QML_DIR / "views" / "QuickCopyView.qml").read_text(encoding="utf-8")
    library = (QML_DIR / "views" / "LibraryView.qml").read_text(encoding="utf-8")

    assert 'text: model ? model.name : ""' in skill_item
    assert 'model.project + " • " + model.category' not in skill_item
    assert "root.compactRows ? 32 : 54" in skill_item
    assert "delegate: SkillItem" in quick_copy
    assert "delegate: SkillItem" in library


def test_skill_rows_use_cached_model_grouping_for_smooth_collapse():
    skill_item = (QML_DIR / "SkillItem.qml").read_text(encoding="utf-8")
    qt_model_py = (QML_DIR.parent / "core" / "models" / "qt_model.py").read_text(encoding="utf-8")
    filter_engine_py = (QML_DIR.parent / "core" / "models" / "filter_engine.py").read_text(encoding="utf-8")

    assert "model.isFirstInSubcategory" in skill_item
    assert "model.isMainCollapsed" in skill_item
    assert "model.isSubCollapsed" in skill_item
    assert "get_skill_at(index - 1)" not in skill_item
    assert "Behavior on height" not in skill_item
    assert "IsFirstInSubcategoryRole" in qt_model_py
    assert "build_visible_rows" in filter_engine_py


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


def test_quick_copy_search_restoration():
    quick_copy = (QML_DIR / "views" / "QuickCopyView.qml").read_text(encoding="utf-8")
    assert "searchInput.text = AppController.quickCopyModel.filterText" in quick_copy


def test_quick_copy_client_format_icons_resizing():
    quick_copy = (QML_DIR / "views" / "QuickCopyView.qml").read_text(encoding="utf-8")

    # Verify the Image dimensions inside clientBtn contentItem are reduced to 16
    assert "sourceSize.width: 16" in quick_copy
    assert "sourceSize.height: 16" in quick_copy
    assert "sourceSize.width: 20" not in quick_copy
    assert "sourceSize.height: 20" not in quick_copy

    # Verify that the Image is wrapped in an Item container and has explicit dimensions & centering anchors
    assert "contentItem: Item {" in quick_copy
    assert "anchors.centerIn: parent" in quick_copy
    assert "width: 16" in quick_copy
    assert "height: 16" in quick_copy

    # Verify the client format buttons background has radius set to half of the width to make it a perfect circle
    assert "radius: width / 2" in quick_copy


def test_delete_buttons_use_trashcan_emoji():
    """Verify that all delete/remove buttons across main views use '🗑️' instead of 'Del'."""
    quick_copy = (QML_DIR / "views" / "QuickCopyView.qml").read_text(encoding="utf-8")
    library = (QML_DIR / "views" / "LibraryView.qml").read_text(encoding="utf-8")
    updates = (QML_DIR / "views" / "UpdatesView.qml").read_text(encoding="utf-8")

    # Verify no legacy "Del" icons exist on delete buttons
    assert 'iconText: "Del"' not in quick_copy
    assert 'iconText: "Del"' not in library
    assert 'iconText: "Del"' not in updates

    # Verify trashcan icon is used instead
    assert 'iconText: "🗑️"' in quick_copy
    assert 'iconText: "🗑️"' in library
    # Expect 2 occurrences in updates (packages and projects remove buttons)
    assert updates.count('iconText: "🗑️"') == 2


def test_scrollbar_presence_in_lists():
    """Verify that both QuickCopyView and LibraryView have vertical scrollbars in their list views."""
    quick_copy = (QML_DIR / "views" / "QuickCopyView.qml").read_text(encoding="utf-8")
    library = (QML_DIR / "views" / "LibraryView.qml").read_text(encoding="utf-8")

    assert "ScrollBar.vertical: ScrollBar" in quick_copy
    assert "ScrollBar.vertical: ScrollBar" in library


def test_expand_collapse_arrow_icons_presence_and_dark_mode():
    """Verify that new expand/collapse SVG arrows are present and properly themed for dark mode in QML files."""
    assets_dir = Path(__file__).resolve().parent.parent / "assets" / "ui"

    # 1. Verify files exist
    assert (assets_dir / "collapse-arrow-icon-light.svg").is_file()
    assert (assets_dir / "collapse-arrow-icon-dark.svg").is_file()
    assert (assets_dir / "expand-arrow-icon-light.svg").is_file()
    assert (assets_dir / "expand-arrow-icon-dark.svg").is_file()

    # 2. Verify legacy icons are not referenced in active QML files
    for qml_file in QML_DIR.rglob("*.qml"):
        text = qml_file.read_text(encoding="utf-8")
        assert "ui/collapse.svg" not in text, f"Legacy collapse.svg reference found in {qml_file.name}"
        assert "ui/expand.svg" not in text, f"Legacy expand.svg reference found in {qml_file.name}"

    # 3. Verify new icons are used in QML files and conditionally toggle dark/light variants
    quick_copy = (QML_DIR / "views" / "QuickCopyView.qml").read_text(encoding="utf-8")
    library = (QML_DIR / "views" / "LibraryView.qml").read_text(encoding="utf-8")
    skill_item = (QML_DIR / "SkillItem.qml").read_text(encoding="utf-8")
    category_header = (QML_DIR / "CategoryHeader.qml").read_text(encoding="utf-8")

    for file_content, file_name in [
        (quick_copy, "QuickCopyView.qml"),
        (library, "LibraryView.qml"),
        (skill_item, "SkillItem.qml"),
        (category_header, "CategoryHeader.qml")
    ]:
        assert "ui/collapse-arrow-icon-dark.svg" in file_content, f"Missing dark collapse icon in {file_name}"
        assert "ui/collapse-arrow-icon-light.svg" in file_content, f"Missing light collapse icon in {file_name}"
        assert "ui/expand-arrow-icon-dark.svg" in file_content, f"Missing dark expand icon in {file_name}"
        assert "ui/expand-arrow-icon-light.svg" in file_content, f"Missing light expand icon in {file_name}"

    # 4. Verify high-resolution/high-DPI SVG rendering quality properties are present
    assert "sourceSize.width: 72" in quick_copy, "QuickCopyView expand/collapse icon sourceSize should be high resolution (72)"
    assert "sourceSize.width: 72" in library, "LibraryView expand/collapse icon sourceSize should be high resolution (72)"
    assert "sourceSize.width: 40" in skill_item, "SkillItem expand/collapse icon sourceSize should be high resolution (40)"
    assert "sourceSize.width: 56" in category_header, "CategoryHeader expand/collapse icon sourceSize should be high resolution (56)"

    # 5. Verify layout sizing properties are present to prevent stretching inside RowLayouts
    assert "width: 16" in quick_copy, "QuickCopyView icon needs width to size correctly inside the button"
    assert "width: 16" in library, "LibraryView icon needs width to size correctly inside the button"
    assert "Layout.preferredWidth: 10" in skill_item, "SkillItem subcategory icon needs Layout.preferredWidth inside RowLayout"
    assert "Layout.preferredWidth: 14" in category_header, "CategoryHeader category icon needs Layout.preferredWidth inside RowLayout"


def test_search_input_uses_icon_instead_of_text_label():
    """Verify that GlassSearchInput uses a search icon instead of the text label 'Search'."""
    search_input = (QML_DIR / "GlassSearchInput.qml").read_text(encoding="utf-8")

    # Verify legacy text label is removed
    assert 'text: "Search"' not in search_input

    # Verify search icon '🔍' is used
    assert 'text: "🔍"' in search_input

    # Verify that leftPadding is set to a clean fixed value for permanent visibility,
    # or at least that it handles the new icon size elegantly.
    assert "leftPadding: 36" in search_input or "leftPadding: 40" in search_input


def test_search_input_scoping_resolution():
    """Verify that GlassSearchInput has renamed its ID to rootSearchField to resolve scoping conflicts."""
    search_input = (QML_DIR / "GlassSearchInput.qml").read_text(encoding="utf-8")

    # The root ID should be rootSearchField, not control
    assert "id: rootSearchField" in search_input
    assert "id: control" not in search_input

    # All references to control should be replaced by rootSearchField
    assert "control.activeFocus" not in search_input
    assert "control.text" not in search_input
    assert "control.forceActiveFocus" not in search_input

    # Ensure clearButton onClicked and visibility reference rootSearchField
    assert "rootSearchField.activeFocus" in search_input
    assert "rootSearchField.text" in search_input


def test_search_input_clear_button_placement():
    """Verify that GlassSearchInput places the IconButton (clear button) as a direct child of the TextField, not nested inside the background property."""
    search_input = (QML_DIR / "GlassSearchInput.qml").read_text(encoding="utf-8")

    # Find the start of the background property block
    bg_index = search_input.find("background: Rectangle {")
    assert bg_index != -1, "Could not find background block in GlassSearchInput.qml"

    # Find theIconButton declaration
    icon_btn_index = search_input.find("IconButton {")
    assert icon_btn_index != -1, "Could not find IconButton in GlassSearchInput.qml"

    # Let's count open/close braces from bg_index to find where background block ends
    brace_count = 0
    bg_end_index = -1
    for i in range(bg_index + len("background: "), len(search_input)):
        char = search_input[i]
        if char == "{":
            brace_count += 1
        elif char == "}":
            brace_count -= 1
            if brace_count == 0:
                bg_end_index = i
                break

    assert bg_end_index != -1, "Could not find the end of background block"

    # The IconButton MUST be defined AFTER the background block has ended to be a direct child of the TextField
    assert icon_btn_index > bg_end_index, "IconButton (clear button) is nested inside the background block, preventing mouse event propagation!"


def test_no_color_string_concatenation():
    """Verify that QML files do not use string concatenation on Theme color properties (which leads to invalid colors)."""
    color_properties = [
        "accent", "appBackground", "glassPill", "glassHover", "glassActive",
        "sidebarBackground", "glassBorder", "glassInnerBorder", "glassOuterBorder",
        "glassShadow", "separator", "disabledControl", "selectedRow",
        "selectedRowHover", "selectedRowBorder", "dangerHover", "label",
        "secondaryLabel", "success", "danger", "hoverBackground"
    ]
    pattern = re.compile(r"Theme\.(" + "|".join(color_properties) + r")\s*\+")

    offenders = []
    for path in QML_DIR.rglob("*.qml"):
        text = path.read_text(encoding="utf-8")
        for line_num, line in enumerate(text.splitlines(), 1):
            if pattern.search(line):
                offenders.append(f"{path.name}:{line_num} -> {line.strip()}")

    assert offenders == [], f"Found color string concatenation: {offenders}"

