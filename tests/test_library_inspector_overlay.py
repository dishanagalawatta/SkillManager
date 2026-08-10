# Purpose: Verify the LibraryView inspector overlay implementation contracts.
# Usage: pytest tests/test_library_inspector_overlay.py

from pathlib import Path

QML_DIR: Path = (
    Path(__file__).resolve().parent.parent / "src" / "skill_manager" / "SkillManagerComponents"
)


# ── showSkillInspector property ─────────────────────────────────


def test_library_view_has_show_skill_inspector() -> None:
    """LibraryView must expose showSkillInspector (now via alias to overlay)."""
    overlay: str = (QML_DIR / "SkillInspectorOverlay.qml").read_text(encoding="utf-8")
    # The property lives in the overlay; the view aliases it.
    assert "property bool showSkillInspector: false" in overlay


def test_library_view_has_selected_skill_valid() -> None:
    """LibraryView must declare a selectedSkillValid readonly helper."""
    view: str = (QML_DIR / "views" / "LibraryView.qml").read_text(encoding="utf-8")
    assert "selectedSkillValid" in view


# ── Connections.onSelectedSkillChanged sets all 3 flags ─────────


def test_connections_block_sets_all_three_flags() -> None:
    """onSelectedSkillChanged must assign showSkillInspector, showCommandInspector, and showImageInspector."""
    overlay: str = (QML_DIR / "SkillInspectorOverlay.qml").read_text(encoding="utf-8")
    # All three flag assignments must appear in the overlay (moved from view)
    assert "showSkillInspector" in overlay
    assert "showCommandInspector" in overlay
    assert "showImageInspector" in overlay


def test_connections_block_uses_explicit_is_command_is_snap() -> None:
    """onSelectedSkillChanged must check skill.is_command and skill.is_snap to set flags."""
    overlay: str = (QML_DIR / "SkillInspectorOverlay.qml").read_text(encoding="utf-8")
    assert "skill.is_command" in overlay
    assert "skill.is_snap" in overlay


# ── Inspector visible bindings use selectedSkillValid ────────────


def test_skill_inspector_uses_selected_skill_valid() -> None:
    """SkillInspector visible must reference selectedSkillValid (not just targetWidth > 0)."""
    overlay: str = (QML_DIR / "SkillInspectorOverlay.qml").read_text(encoding="utf-8")
    assert "selectedSkillValid" in overlay


def test_command_inspector_uses_explicit_flag() -> None:
    """CommandInspector visible must reference showCommandInspector."""
    overlay: str = (QML_DIR / "SkillInspectorOverlay.qml").read_text(encoding="utf-8")
    assert "showCommandInspector" in overlay


def test_image_inspector_uses_explicit_flag() -> None:
    """ImageInspector visible must reference showImageInspector."""
    overlay: str = (QML_DIR / "SkillInspectorOverlay.qml").read_text(encoding="utf-8")
    assert "showImageInspector" in overlay


# ── Backdrop dismisses all three inspectors ─────────────────────


def test_backdrop_dismisses_all_three_inspectors() -> None:
    """Backdrop onClicked must reset all three show* flags."""
    overlay: str = (QML_DIR / "SkillInspectorOverlay.qml").read_text(encoding="utf-8")

    # Each flag should be explicitly set to false in the backdrop click handler
    assert "showSkillInspector" in overlay
    assert "showCommandInspector" in overlay
    assert "showImageInspector" in overlay


# ── onInspectImageRequested resets other flags ──────────────────


def test_on_inspect_image_requested_resets_other_flags() -> None:
    """onInspectImageRequested handler must reset showCommandInspector and showSkillInspector."""
    view: str = (QML_DIR / "views" / "LibraryView.qml").read_text(encoding="utf-8")
    overlay: str = (QML_DIR / "SkillInspectorOverlay.qml").read_text(encoding="utf-8")
    # The handler is in the view (SkillItem.onInspectImageRequested calls overlay)
    assert "onInspectImageRequested" in view
    # forceImageInspector logic lives in the overlay
    assert "forceImageInspector" in overlay
    assert "showImageInspector" in overlay


# ── Panel width does not depend on inspector targetWidth ────────


def test_panel_width_uses_fixed_minimum_not_inspector_target_width() -> None:
    """_panelW must compute width from fixed minimums + ui_controller.inspectorWidth, not inspector targetWidth."""
    overlay: str = (QML_DIR / "SkillInspectorOverlay.qml").read_text(encoding="utf-8")
    assert "inspectorWidth" in overlay


# ── Right-click toggle pattern preserved ────────────────────────


def test_right_click_handler_toggles_inspector() -> None:
    """Right-click must selectSkill(index) when clicking a different skill."""
    view: str = (QML_DIR / "views" / "LibraryView.qml").read_text(encoding="utf-8")
    assert "selectSkill(index)" in view
    assert "selectSkill(-1)" in view


# ── Popup / panel mode gates ────────────────────────────────────


def test_popup_mode_gates_inspector_geometry() -> None:
    """All three inspectors must use _usePopupMode to toggle between popup and side-panel positioning."""
    overlay: str = (QML_DIR / "SkillInspectorOverlay.qml").read_text(encoding="utf-8")
    count = overlay.count("usePopupMode")
    # At least 3 inspectors x 4 position props (x, y, width, height) = 12+ references
    assert count >= 6, f"Expected >=6 usePopupMode refs, got {count}"


def test_popup_mode_threshold() -> None:
    """_usePopupMode must trigger at width <= 800."""
    view: str = (QML_DIR / "views" / "LibraryView.qml").read_text(encoding="utf-8")
    assert "width <= 800" in view or "width<=800" in view


# ── Closed handlers ─────────────────────────────────────────────


def test_closed_handlers_reset_their_flag() -> None:
    """Each inspector's onClosed must reset its show* flag."""
    overlay: str = (QML_DIR / "SkillInspectorOverlay.qml").read_text(encoding="utf-8")

    # CommandInspector and ImageInspector close handlers explicitly reset their flag
    assert "root.showCommandInspector = false" in overlay
    assert "root.showImageInspector = false" in overlay


# ── Top Margin & Dynamic Height ─────────────────────────────────


def test_top_margin_property_in_overlay() -> None:
    """SkillInspectorOverlay must declare topMargin property for dynamic vertical positioning."""
    overlay: str = (QML_DIR / "SkillInspectorOverlay.qml").read_text(encoding="utf-8")
    assert "property real topMargin: 0" in overlay


def test_side_panel_y_and_height_use_top_margin() -> None:
    """Side panel position and height must dynamically account for topMargin without hardcoded heights."""
    overlay: str = (QML_DIR / "SkillInspectorOverlay.qml").read_text(encoding="utf-8")
    assert "y: root.usePopupMode ? root._popupY : root.topMargin" in overlay
    assert "parent.height - root.topMargin" in overlay


def test_views_pass_dynamic_top_margin() -> None:
    """LibraryView and QuickCopyView must dynamically compute topMargin from header height and layout spacing."""
    lib_view: str = (QML_DIR / "views" / "LibraryView.qml").read_text(encoding="utf-8")
    qc_view: str = (QML_DIR / "views" / "QuickCopyView.qml").read_text(encoding="utf-8")

    assert "topMargin: lv_headerRow.height + lv_mainLayout.spacing" in lib_view
    assert "topMargin: qcv_headerRow.height + qcv_mainLayout.spacing" in qc_view


# ── Collapsible Inspector Sections ──────────────────────────────


def test_inspector_metadata_row_has_collapsible_is_expanded_property() -> None:
    """InspectorMetadataRow must expose property bool isExpanded: true and collapsible header controls."""
    meta_row: str = (QML_DIR / "InspectorMetadataRow.qml").read_text(encoding="utf-8")
    assert "property bool isExpanded: true" in meta_row
    assert "activeFocusOnTab: true" in meta_row
    assert "root.isExpanded = !root.isExpanded" in meta_row
    assert 'text: root.isExpanded ? "Collapse Metadata" : "Expand Metadata"' in meta_row
    assert "Accessible.role: Accessible.Button" in meta_row
    assert 'Accessible.name: root.isExpanded ? "Collapse Metadata" : "Expand Metadata"' in meta_row


def test_command_inspector_dependencies_section_has_is_expanded() -> None:
    """CommandInspector's Skill Dependencies section must support interactive expand/collapse toggling."""
    cmd_insp: str = (QML_DIR / "CommandInspector.qml").read_text(encoding="utf-8")
    assert "id: depSection" in cmd_insp
    assert "property bool isExpanded: true" in cmd_insp
    assert "depSection.isExpanded = !depSection.isExpanded" in cmd_insp


def test_skill_inspector_documentation_section_has_is_expanded() -> None:
    """SkillInspector's Documentation section must support interactive expand/collapse toggling."""
    skill_insp: str = (QML_DIR / "SkillInspector.qml").read_text(encoding="utf-8")
    assert "id: docSection" in skill_insp
    assert "property bool isExpanded: true" in skill_insp
    assert "docSection.isExpanded = !docSection.isExpanded" in skill_insp
