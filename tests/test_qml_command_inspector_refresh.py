"""QML binding test for CommandInspector refresh.

Verifies that the ``selectedSkillChanged`` signal triggers re-binding
of ``skill: AppController.selectedSkill`` by checking that the
``_selected_skill`` property is updated when the signal fires.

This is a lightweight Python-level test of the signal→binding pipeline.
Full QML rendering tests are deferred — the integration tests in
``test_ops_controller.py`` and ``test_app_controller.py`` already
validate end-to-end that ``discover_single`` works for command files.
"""

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

    app_controller._selected_skill = {
        "local_path": str(cmd_file),
        "name": "Cmd",
        "body_content": "old body",
    }

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
    assert app_controller._selected_skill.get("body_content") == "new body", (
        f"body_content should be 'new body', got {app_controller._selected_skill.get('body_content')}"
    )
