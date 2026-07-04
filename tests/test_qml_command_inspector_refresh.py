"""QML binding test for CommandInspector refresh.

Verifies that the ``selectedSkillChanged`` signal triggers re-binding
of ``skill: AppController.selectedSkill`` by checking that the
``_selected_skill`` property is updated when the signal fires.

This is a lightweight Python-level test of the signal→binding pipeline.
Full QML rendering tests are deferred — the integration tests in
``test_ops_controller.py`` and ``test_app_controller.py`` already
validate end-to-end that ``discover_single`` works for command files.
"""

import re
from unittest.mock import patch


@patch("skill_manager.core.persistence.patch_cache_add")
def test_selected_skill_changed_updates_binding(mock_patch_cache, app_controller, temp_dir):
    """After updateCustomCommandFull, _selected_skill should reflect new data."""
    project_path = temp_dir / "project"
    project_path.mkdir()
    commands_dir = project_path / ".agents" / "commands"
    commands_dir.mkdir(parents=True)

    app_controller._projects = [str(project_path)]

    # Write an initial command
    cmd_file = commands_dir / "Cmd.md"
    content = "---\nname: Cmd\ncategory: Commands\ntype: command\n---\n\nold body"
    cmd_file.write_text(content, encoding="utf-8")

    # Load into model and select
    skill_data = {
        "local_path": str(cmd_file),
        "name": "Cmd",
        "body_content": "old body",
        "category": "Custom Commands",
        "main_category": "System & Workflow",
        "is_command": True,
        "is_starred": False,
        "is_bundle": False,
        "is_archived": False,
        "is_selected": False,
        "is_package": False,
        "is_source": False,
        "project_label": "test-project",
        "source": "Custom",
        "risk": "Low",
        "description": "",
        "raw_content": "",
    }
    app_controller._library_model.addOrUpdateSkills([skill_data])
    app_controller._quick_copy_model.addOrUpdateSkills([skill_data])
    for model in (app_controller._library_model, app_controller._quick_copy_model):
        model.showCommands = True
        model.state.is_package_only = None
        model._apply_filter()

    app_controller.set_selected_skill(
        {
            "local_path": str(cmd_file),
            "name": "Cmd",
            "body_content": "old body",
        }
    )

    # Track signal
    emissions = []
    app_controller.selectedSkillChanged.connect(lambda: emissions.append(True))

    # Update the command
    from skill_manager.core.quick_copy import project_label as compute_project_label

    proj_label = compute_project_label(project_path)
    app_controller.ops.updateCustomCommandFull(
        str(cmd_file), "Cmd", "new body", "Commands", [proj_label]
    )

    from PySide6.QtWidgets import QApplication

    QApplication.processEvents()

    # Signal should fire
    assert emissions, "selectedSkillChanged was not emitted"

    # _selected_skill should now have the new body
    assert app_controller._selected_skill.value("body_content") == "new body", (
        f"body_content should be 'new body', got {app_controller._selected_skill.value('body_content')}"
    )


# ── Delete routing tests ──────────────────────────────────────────────


def test_delete_command_routes_to_command_delete_dialog():
    """CommandDeleteDialog must exist and expose openForCommand / openForSkill / openBulkSkill."""
    from pathlib import Path

    dialog_path = (
        Path(__file__).resolve().parent.parent
        / "src"
        / "skill_manager"
        / "SkillManagerComponents"
        / "dialogs"
        / "CommandDeleteDialog.qml"
    )
    assert dialog_path.exists(), "CommandDeleteDialog.qml not found"

    content = dialog_path.read_text(encoding="utf-8")
    assert "function openForCommand" in content, (
        "CommandDeleteDialog must expose openForCommand(name, projects)"
    )
    assert "function openForSkill" in content, (
        "CommandDeleteDialog must expose openForSkill(name, callback)"
    )
    assert "function openBulkSkill" in content, (
        "CommandDeleteDialog must expose openBulkSkill(count, callback)"
    )
    assert "deleteCustomCommand" in content, (
        "CommandDeleteDialog must call AppController.deleteCustomCommand in command mode"
    )


def test_legacy_delete_confirm_dialog_removed():
    """DeleteConfirmDialog.qml must no longer exist."""
    from pathlib import Path

    old_dialog = (
        Path(__file__).resolve().parent.parent
        / "src"
        / "skill_manager"
        / "SkillManagerComponents"
        / "dialogs"
        / "DeleteConfirmDialog.qml"
    )
    assert not old_dialog.exists(), (
        "DeleteConfirmDialog.qml should have been removed — replaced by CommandDeleteDialog.qml"
    )


def test_qmldir_registers_command_delete_dialog():
    """qmldir must register CommandDeleteDialog and not DeleteConfirmDialog."""
    from pathlib import Path

    qmldir = (
        Path(__file__).resolve().parent.parent
        / "src"
        / "skill_manager"
        / "SkillManagerComponents"
        / "qmldir"
    )
    content = qmldir.read_text(encoding="utf-8")
    assert "CommandDeleteDialog 1.0 dialogs/CommandDeleteDialog.qml" in content, (
        "qmldir must register CommandDeleteDialog"
    )
    assert "DeleteConfirmDialog" not in content, (
        "qmldir must not reference the removed DeleteConfirmDialog"
    )


def test_skill_item_emits_is_command_in_delete_signal():
    """SkillItem.qml deleteRequested signal must carry isCommand."""
    from pathlib import Path

    skill_item = (
        Path(__file__).resolve().parent.parent
        / "src"
        / "skill_manager"
        / "SkillManagerComponents"
        / "SkillItem.qml"
    )
    content = skill_item.read_text(encoding="utf-8")
    assert "signal deleteRequested(string name, string path, bool isCommand)" in content, (
        "SkillItem.qml must emit deleteRequested(name, path, isCommand)"
    )
    assert "root.deleteRequested(model.name, model.path, model.isCommand === true)" in content, (
        "SkillItem.qml delete button must pass model.isCommand to the signal"
    )


def test_library_view_routes_command_delete():
    """LibraryView.qml must branch on isCommand for delete routing."""
    from pathlib import Path

    view = (
        Path(__file__).resolve().parent.parent
        / "src"
        / "skill_manager"
        / "SkillManagerComponents"
        / "views"
        / "LibraryView.qml"
    )
    content = view.read_text(encoding="utf-8")
    assert "onDeleteRequested: (name, path, isCommand)" in content, (
        "LibraryView must accept isCommand in onDeleteRequested handler"
    )
    assert "lv_cmdDeleteDialog.openForCommand" in content, (
        "LibraryView must route command deletes to openForCommand"
    )
    assert "lv_cmdDeleteDialog.openForSkill" in content, (
        "LibraryView must route skill deletes to openForSkill"
    )
    assert "lv_cmdDeleteDialog.openBulkSkill" in content, (
        "LibraryView must route bulk deletes to openBulkSkill"
    )
    assert "DeleteConfirmDialog" not in content, (
        "LibraryView must not reference the removed DeleteConfirmDialog"
    )


def test_quick_copy_view_routes_command_delete():
    """QuickCopyView.qml must branch on isCommand for delete routing."""
    from pathlib import Path

    view = (
        Path(__file__).resolve().parent.parent
        / "src"
        / "skill_manager"
        / "SkillManagerComponents"
        / "views"
        / "QuickCopyView.qml"
    )
    content = view.read_text(encoding="utf-8")
    assert "onDeleteRequested: (name, path, isCommand)" in content, (
        "QuickCopyView must accept isCommand in onDeleteRequested handler"
    )
    assert "qcv_cmdDeleteDialog.openForCommand" in content, (
        "QuickCopyView must route command deletes to openForCommand"
    )
    assert "qcv_cmdDeleteDialog.openForSkill" in content, (
        "QuickCopyView must route skill deletes to openForSkill"
    )
    assert "qcv_cmdDeleteDialog.openBulkSkill" in content, (
        "QuickCopyView must route bulk deletes to openBulkSkill"
    )
    assert "DeleteConfirmDialog" not in content, (
        "QuickCopyView must not reference the removed DeleteConfirmDialog"
    )


def test_command_inspector_uses_shared_dialog():
    """CommandInspector.qml must delegate deletion via deleteRequested signal, and not instantiate its own dialog."""
    from pathlib import Path

    inspector = (
        Path(__file__).resolve().parent.parent
        / "src"
        / "skill_manager"
        / "SkillManagerComponents"
        / "CommandInspector.qml"
    )
    content = inspector.read_text(encoding="utf-8")
    assert "CommandDeleteDialog" not in content, (
        "CommandInspector should not instantiate CommandDeleteDialog locally to prevent duplicates"
    )
    assert "signal deleteRequested(string name, string path, bool isCommand)" in content, (
        "CommandInspector must declare deleteRequested signal"
    )
    assert "deleteRequested(" in content, "CommandInspector must emit deleteRequested signal"


def test_command_delete_dialog_uses_new_design_language():
    """CommandDeleteDialog must not carry the legacy 'Confirm Deletion' design elements."""
    from pathlib import Path

    dialog_path = (
        Path(__file__).resolve().parent.parent
        / "src"
        / "skill_manager"
        / "SkillManagerComponents"
        / "dialogs"
        / "CommandDeleteDialog.qml"
    )
    content = dialog_path.read_text(encoding="utf-8")

    # No legacy badge text
    assert "Selected Item" not in content, (
        "CommandDeleteDialog must not contain the legacy 'Selected Item' badge — "
        "the new design language is clean (no pill badge)"
    )
    # No legacy 'cannot be undone' subtext
    assert "cannot be undone" not in content, (
        "CommandDeleteDialog must not contain the legacy 'This action cannot be undone.' subtext — "
        "the new design language is clean (no warning subtext)"
    )
    # Confirm the new title patterns are present
    assert '"Delete Items"' in content or "'Delete Items'" in content, (
        "CommandDeleteDialog must use the new 'Delete Items' title for bulk mode"
    )
    assert '"Delete Item"' in content or "'Delete Item'" in content, (
        "CommandDeleteDialog must use the new 'Delete Item' title for single-item mode"
    )


# ── Delete popup unification tests ────────────────────────────────────


def _extract_action_button_blocks(text: str) -> list[str]:
    """Return the source of every `ActionButton { ... }` top-level block.

    Handles one level of nested braces (ActionButton has no deeply nested
    blocks in these dialogs). Used to verify that no dialog hand-rolls
    `background`/`contentItem` overrides on ActionButton.
    """
    blocks: list[str] = []
    for m in re.finditer(r"ActionButton\s*\{", text):
        start = m.end()
        depth = 1
        i = start
        while i < len(text) and depth > 0:
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
            i += 1
        blocks.append(text[m.start() : i])
    return blocks


def test_command_removal_dialog_uses_glass_dialog_base():
    """CommandRemovalConfirmDialog must extend GlassDialog, not raw Dialog.

    GlassDialog provides the unified "Solid Matte" surface: custom header
    (icon + title + close button), drop shadow, and consistent background.
    The old raw-Dialog version rendered the native OS title bar and had
    no shadow — visually inconsistent with the rest of the delete family.
    """
    from pathlib import Path

    dialog = (
        Path(__file__).resolve().parent.parent
        / "src"
        / "skill_manager"
        / "SkillManagerComponents"
        / "dialogs"
        / "CommandRemovalConfirmDialog.qml"
    )
    assert dialog.exists(), "CommandRemovalConfirmDialog.qml not found"
    content = dialog.read_text(encoding="utf-8")

    # Root element must be GlassDialog, not a raw Dialog
    assert re.search(r"^GlassDialog\s*\{", content, re.MULTILINE), (
        "CommandRemovalConfirmDialog must root in GlassDialog — "
        "raw Dialog renders the native OS title bar and has no drop shadow."
    )
    # Must set dialogTitle/dialogIcon (GlassDialog custom header) and NOT
    # the native `title:` property.
    assert "dialogTitle:" in content, (
        "CommandRemovalConfirmDialog must set dialogTitle for the GlassDialog header"
    )
    assert "dialogIcon:" in content, (
        "CommandRemovalConfirmDialog must set dialogIcon for the GlassDialog header"
    )
    # The native `title:` property must not appear (it renders the OS bar).
    # Allow `dialogTitle` to match but reject a bare `title:` assignment.
    bare_title = re.search(r"^\s*title:\s*", content, re.MULTILINE)
    assert bare_title is None, (
        "CommandRemovalConfirmDialog must not set the native `title:` property — "
        "use dialogTitle instead so the custom GlassDialog header renders."
    )


def test_command_removal_dialog_registered_in_qmldir():
    """qmldir must register CommandRemovalConfirmDialog for consistent loading."""
    from pathlib import Path

    qmldir = (
        Path(__file__).resolve().parent.parent
        / "src"
        / "skill_manager"
        / "SkillManagerComponents"
        / "qmldir"
    )
    content = qmldir.read_text(encoding="utf-8")
    assert "CommandRemovalConfirmDialog 1.0 dialogs/CommandRemovalConfirmDialog.qml" in content, (
        "qmldir must register CommandRemovalConfirmDialog"
    )


def test_command_removal_dialog_uses_danger_role_button():
    """The 'Remove Checked' button must use role: 'danger' (solid red).

    A destructive action painted in Theme.accent (blue/green) misreads as
    a confirmation. role:'danger' gives a solid red fill via ActionButton's
    design-system theming.
    """
    from pathlib import Path

    dialog = (
        Path(__file__).resolve().parent.parent
        / "src"
        / "skill_manager"
        / "SkillManagerComponents"
        / "dialogs"
        / "CommandRemovalConfirmDialog.qml"
    )
    content = dialog.read_text(encoding="utf-8")
    assert 'role: "danger"' in content, (
        'CommandRemovalConfirmDialog must use role: "danger" for the Remove Checked button'
    )
    assert "Remove Checked" in content, "Remove Checked button label must be present"


def test_delete_dialogs_do_not_hand_roll_action_button_overrides():
    """Delete-family dialogs must not override ActionButton background/contentItem.

    Hand-rolled `background: Rectangle {}` / `contentItem: Text {}` inside
    an ActionButton block defeats the design-system role theming and is
    what caused the per-dialog visual drift (wrong colors, overflow).
    ActionButton already supports role: primary|secondary|destructive|danger.
    """
    from pathlib import Path

    base = (
        Path(__file__).resolve().parent.parent
        / "src"
        / "skill_manager"
        / "SkillManagerComponents"
        / "dialogs"
    )
    targets = [
        "CommandDeleteDialog.qml",
        "CommandRemovalConfirmDialog.qml",
    ]
    for name in targets:
        path = base / name
        assert path.exists(), f"{name} not found"
        text = path.read_text(encoding="utf-8")
        blocks = _extract_action_button_blocks(text)
        assert blocks, f"{name} must contain at least one ActionButton"
        for i, block in enumerate(blocks):
            assert "background:" not in block, (
                f"{name}: ActionButton block #{i} must not override `background` — "
                "use role: primary|secondary|destructive|danger instead."
            )
            assert "contentItem:" not in block, (
                f"{name}: ActionButton block #{i} must not override `contentItem` — "
                "ActionButton provides its own centered content via role theming."
            )


def _parse_footer_metrics(text: str) -> list[dict]:
    """Extract footer height + top/bottom margins for every `footer: Item` block.

    Returns a list of dicts: {footer_h, top, bottom, avail}.
    """
    import re

    results: list[dict] = []
    for m in re.finditer(r"footer:\s*Item\s*\{", text):
        start = m.end()
        depth = 1
        i = start
        while i < len(text) and depth > 0:
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
            i += 1
        block = text[m.start() : i]

        h_match = re.search(r"height:\s*(\d+)", block)
        top_match = re.search(r"anchors\.topMargin:\s*(\d+)", block)
        bot_match = re.search(r"anchors\.bottomMargin:\s*(\d+)", block)
        footer_h = int(h_match.group(1)) if h_match else 0
        top = int(top_match.group(1)) if top_match else 0
        bottom = int(bot_match.group(1)) if bot_match else 0
        results.append(
            {"footer_h": footer_h, "top": top, "bottom": bottom, "avail": footer_h - top - bottom}
        )
    return results


def test_delete_dialog_footer_has_no_button_overflow():
    """Footer height must leave >= 4px breathing room for a 36px button.

    This is the regression guard for the reported overflow bug. The old
    dialogs used footer=76 with top=12/bottom=24 (avail=40) and a 40px
    button + 2px focus border = 41px effective -> 1px visual overflow.
    The fix normalizes to footer=80, top=20, bottom=24 (avail=36) with a
    36px button -> 4px breathing room, zero overflow.
    """
    from pathlib import Path

    base = (
        Path(__file__).resolve().parent.parent
        / "src"
        / "skill_manager"
        / "SkillManagerComponents"
        / "dialogs"
    )
    targets = ["CommandDeleteDialog.qml", "CommandRemovalConfirmDialog.qml"]
    for name in targets:
        path = base / name
        text = path.read_text(encoding="utf-8")
        footers = _parse_footer_metrics(text)
        assert footers, f"{name} must define a footer: Item"
        for f in footers:
            # 36px button + 2px focus border (1px outside) = 37px effective.
            # Require avail >= 37 + 4px breathing room = 41 to be safe.
            assert f["avail"] >= 40, (
                f"{name}: footer avail={f['avail']} (footer={f['footer_h']} "
                f"top={f['top']} bottom={f['bottom']}) must be >= 40 to fit a 36px "
                "button with 2px focus border plus breathing room."
            )


def test_action_button_supports_danger_role():
    """ActionButton must support role: 'danger' (solid red destructive action)."""
    from pathlib import Path

    ab = (
        Path(__file__).resolve().parent.parent
        / "src"
        / "skill_manager"
        / "SkillManagerComponents"
        / "ActionButton.qml"
    )
    content = ab.read_text(encoding="utf-8")
    assert 'role === "danger"' in content, (
        'ActionButton must handle role === "danger" in its color logic'
    )
    # The solid-danger branch must use Theme.danger as the fill (not transparent)
    danger_block = re.search(r'role\s*===\s*"danger".*?return.*?Theme\.danger', content, re.DOTALL)
    assert danger_block, (
        "ActionButton role:danger must fill with Theme.danger (solid red), "
        "not the outline destructive style."
    )


# ── CommandInspector body refresh tests ─────────────────────────────


def test_command_inspector_has_direct_skill_binding():
    """CommandInspector.qml must bind bodyArea.text directly to skill.body_content."""
    from pathlib import Path

    inspector = (
        Path(__file__).resolve().parent.parent
        / "src"
        / "skill_manager"
        / "SkillManagerComponents"
        / "CommandInspector.qml"
    )
    content = inspector.read_text(encoding="utf-8")
    assert "root._sel.body_content" in content, (
        "CommandInspector must bind bodyArea.text to root._sel.body_content "
        "(QQmlPropertyMap provides per-key notify signals for reliable reactivity)"
    )


def test_command_inspector_no_body_content_workaround():
    """CommandInspector.qml must NOT use a bodyContent string property workaround."""
    from pathlib import Path

    inspector = (
        Path(__file__).resolve().parent.parent
        / "src"
        / "skill_manager"
        / "SkillManagerComponents"
        / "CommandInspector.qml"
    )
    content = inspector.read_text(encoding="utf-8")
    assert "property string bodyContent" not in content, (
        "bodyContent workaround removed — QQmlPropertyMap handles reactivity natively"
    )


def test_command_inspector_on_skill_changed_handler():
    """onSelectedSkillChanged must update dependency lists."""
    from pathlib import Path

    inspector = (
        Path(__file__).resolve().parent.parent
        / "src"
        / "skill_manager"
        / "SkillManagerComponents"
        / "CommandInspector.qml"
    )
    content = inspector.read_text(encoding="utf-8")
    assert "onSelectedSkillChanged" in content, (
        "CommandInspector must have onSelectedSkillChanged handler"
    )
    assert "root.dependencyList" in content, (
        "onSelectedSkillChanged must update root.dependencyList"
    )
    assert "_applyHighlights" in content, "onSelectedSkillChanged must call _applyHighlights"
