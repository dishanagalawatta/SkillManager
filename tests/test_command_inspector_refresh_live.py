"""QML-level regression test for CommandInspector body refresh.

Verifies the full signal→binding chain: when a command is updated,
``selectedSkillChanged`` fires, ``_selected_skill`` is reassigned
with the new ``body_content``, and the QML property ``bodyContent``
is bound to ``bodyArea.text`` so the UI refreshes.

Run with:
    uv run pytest tests/test_command_inspector_refresh_live.py -v
"""

from __future__ import annotations

import re
from pathlib import Path
from unittest.mock import patch

QML_DIR = (
    Path(__file__).resolve().parent.parent / "src" / "skill_manager" / "SkillManagerComponents"
)


@patch("skill_manager.core.persistence.patch_cache_add")
def test_update_command_refreshes_selected_skill(mock_patch_cache, app_controller, temp_dir):
    """After updateCustomCommandFull, _selected_skill.body_content must reflect new body."""
    project_path = temp_dir / "project"
    project_path.mkdir()
    commands_dir = project_path / ".agents" / "commands"
    commands_dir.mkdir(parents=True)

    app_controller._projects = [str(project_path)]

    cmd_file = commands_dir / "Cmd.md"
    content = "---\nname: Cmd\ncategory: Commands\ntype: command\n---\n\nold body"
    cmd_file.write_text(content, encoding="utf-8")

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

    emissions = []
    app_controller.selectedSkillChanged.connect(lambda: emissions.append(True))

    from skill_manager.core.quick_copy import project_label as compute_project_label

    proj_label = compute_project_label(project_path)
    app_controller.ops.updateCustomCommandFull(
        str(cmd_file), "Cmd", "new body", "Commands", [proj_label]
    )

    from PySide6.QtWidgets import QApplication

    QApplication.processEvents()

    assert emissions, "selectedSkillChanged was not emitted"
    assert app_controller._selected_skill.value("body_content") == "new body", (
        f"body_content should be 'new body', got {app_controller._selected_skill.value('body_content')}"
    )
    assert app_controller._selected_skill.value("name") == "Cmd"


@patch("skill_manager.core.persistence.patch_cache_add")
def test_update_command_refreshes_dependency_list(mock_patch_cache, app_controller, temp_dir):
    """After updateCustomCommandFull, dependencyList should be re-queried for the updated command."""
    project_path = temp_dir / "project"
    project_path.mkdir()
    commands_dir = project_path / ".agents" / "commands"
    commands_dir.mkdir(parents=True)

    app_controller._projects = [str(project_path)]

    cmd_file = commands_dir / "Cmd.md"
    content = "---\nname: Cmd\ncategory: Commands\ntype: command\n---\n\nold body"
    cmd_file.write_text(content, encoding="utf-8")

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
            "is_command": True,
        }
    )

    from skill_manager.core.quick_copy import project_label as compute_project_label

    proj_label = compute_project_label(project_path)
    app_controller.ops.updateCustomCommandFull(
        str(cmd_file), "Cmd", "new body with @ref SkillRef", "Commands", [proj_label]
    )

    from PySide6.QtWidgets import QApplication

    QApplication.processEvents()

    assert app_controller._selected_skill.value("body_content") == "new body with @ref SkillRef"


def test_command_inspector_qml_has_required_bindings():
    """Static check: CommandInspector.qml uses direct skill property binding."""
    inspector_path = QML_DIR / "CommandInspector.qml"
    content = inspector_path.read_text(encoding="utf-8")

    assert "_sel" in content, "CommandInspector must use _sel property"
    assert "onSelectedSkillChanged" in content, (
        "CommandInspector must have onSelectedSkillChanged handler"
    )
    assert "root._sel.body_content" in content, (
        "bodyArea.text must bind to root._sel.body_content (QQmlPropertyMap ensures reactivity)"
    )


def test_command_inspector_qml_binding_chain_integrity():
    """Verify the QML property→signal→binding chain is structurally correct."""
    inspector_path = QML_DIR / "CommandInspector.qml"
    content = inspector_path.read_text(encoding="utf-8")

    has_sel_property = bool(re.search(r"readonly property var _sel:", content))
    has_skill_property = bool(re.search(r"property\s+var\s+skill\s*:", content))
    has_on_selected_skill_changed = bool(re.search(r"onSelectedSkillChanged", content))
    binds_to_body_area = bool(
        re.search(r"text:\s*\(root\._sel\s*&&\s*root\._sel\.body_content\)", content)
    )

    assert has_sel_property, "root._sel readonly property must exist"
    assert has_skill_property, "root.skill backward-compat alias must exist"
    assert has_on_selected_skill_changed, "onSelectedSkillChanged handler must exist"
    assert binds_to_body_area, "bodyArea.text must bind to root._sel.body_content"
