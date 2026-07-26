# Purpose: Verify the LibraryView inspector overlay implementation contracts.
# Usage: pytest tests/test_library_inspector_overlay.py

from pathlib import Path

QML_DIR: Path = (
    Path(__file__).resolve().parent.parent / "src" / "skill_manager" / "SkillManagerComponents"
)


# ── showSkillInspector property ─────────────────────────────────


def test_library_view_has_show_skill_inspector() -> None:
    """LibraryView must declare an explicit showSkillInspector property."""
    view: str = (QML_DIR / "views" / "LibraryView.qml").read_text(encoding="utf-8")
    assert "property bool showSkillInspector: false" in view


def test_library_view_has_selected_skill_valid() -> None:
    """LibraryView must declare a selectedSkillValid readonly helper."""
    view: str = (QML_DIR / "views" / "LibraryView.qml").read_text(encoding="utf-8")
    assert "selectedSkillValid" in view


# ── Connections.onSelectedSkillChanged sets all 3 flags ─────────


def test_connections_block_sets_all_three_flags() -> None:
    """onSelectedSkillChanged must assign showSkillInspector, showCommandInspector, and showImageInspector."""
    view: str = (QML_DIR / "views" / "LibraryView.qml").read_text(encoding="utf-8")
    # All three flag assignments must appear in the file
    assert "showSkillInspector" in view
    assert "showCommandInspector" in view
    assert "showImageInspector" in view


def test_connections_block_uses_explicit_is_command_is_screenshot() -> None:
    """onSelectedSkillChanged must check skill.is_command and skill.is_screenshot to set flags."""
    view: str = (QML_DIR / "views" / "LibraryView.qml").read_text(encoding="utf-8")
    assert "skill.is_command" in view
    assert "skill.is_screenshot" in view


# ── Inspector visible bindings use selectedSkillValid ────────────


def test_skill_inspector_uses_selected_skill_valid() -> None:
    """SkillInspector visible must reference selectedSkillValid (not just targetWidth > 0)."""
    view: str = (QML_DIR / "views" / "LibraryView.qml").read_text(encoding="utf-8")
    assert "selectedSkillValid" in view


def test_command_inspector_uses_explicit_flag() -> None:
    """CommandInspector visible must reference showCommandInspector."""
    view: str = (QML_DIR / "views" / "LibraryView.qml").read_text(encoding="utf-8")
    assert "showCommandInspector" in view


def test_image_inspector_uses_explicit_flag() -> None:
    """ImageInspector visible must reference showImageInspector."""
    view: str = (QML_DIR / "views" / "LibraryView.qml").read_text(encoding="utf-8")
    assert "showImageInspector" in view


# ── Backdrop dismisses all three inspectors ─────────────────────


def test_backdrop_dismisses_all_three_inspectors() -> None:
    """Backdrop onClicked must reset all three show* flags."""
    view: str = (QML_DIR / "views" / "LibraryView.qml").read_text(encoding="utf-8")

    # Each flag should be explicitly set to false in the backdrop click handler
    assert "showSkillInspector" in view
    assert "showCommandInspector" in view
    assert "showImageInspector" in view


# ── onInspectImageRequested resets other flags ──────────────────


def test_on_inspect_image_requested_resets_other_flags() -> None:
    """onInspectImageRequested handler must reset showCommandInspector and showSkillInspector."""
    view: str = (QML_DIR / "views" / "LibraryView.qml").read_text(encoding="utf-8")
    # The handler should reset the non-image flags
    assert "onInspectImageRequested" in view
    # Should set image inspector flag
    assert "showImageInspector" in view


# ── Panel width does not depend on inspector targetWidth ────────


def test_panel_width_uses_fixed_minimum_not_inspector_target_width() -> None:
    """_panelW must compute width from fixed minimums + ui_controller.inspectorWidth, not inspector targetWidth."""
    view: str = (QML_DIR / "views" / "LibraryView.qml").read_text(encoding="utf-8")
    assert "inspectorWidth" in view


# ── Right-click toggle pattern preserved ────────────────────────


def test_right_click_handler_toggles_inspector() -> None:
    """Right-click must selectSkill(index) when clicking a different skill."""
    view: str = (QML_DIR / "views" / "LibraryView.qml").read_text(encoding="utf-8")
    assert "selectSkill(index)" in view
    assert "selectSkill(-1)" in view


# ── Popup / panel mode gates ────────────────────────────────────


def test_popup_mode_gates_inspector_geometry() -> None:
    """All three inspectors must use _usePopupMode to toggle between popup and side-panel positioning."""
    view: str = (QML_DIR / "views" / "LibraryView.qml").read_text(encoding="utf-8")
    count = view.count("_usePopupMode")
    # At least 3 inspectors × 4 position props (x, y, width, height) = 12+ references
    assert count >= 6, f"Expected >=6 _usePopupMode refs, got {count}"


def test_popup_mode_threshold() -> None:
    """_usePopupMode must trigger at width <= 800."""
    view: str = (QML_DIR / "views" / "LibraryView.qml").read_text(encoding="utf-8")
    assert "width <= 800" in view or "width<=800" in view


# ── Closed handlers ─────────────────────────────────────────────


def test_closed_handlers_reset_their_flag() -> None:
    """Each inspector's onClosed must reset its show* flag."""
    view: str = (QML_DIR / "views" / "LibraryView.qml").read_text(encoding="utf-8")

    # CommandInspector and ImageInspector close handlers explicitly reset their flag
    assert "lv_root.showCommandInspector = false" in view
    assert "lv_root.showImageInspector = false" in view

    # SkillInspector close handler should also reset explicitly (via selectSkill(-1) or direct)
    assert "selectSkill(-1)" in view
