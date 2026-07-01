import pytest


@pytest.mark.usefixtures("setup_qml_style")
class TestUIOpsFlow:
    def test_delete_skill_ui_updates_model(self, qml_engine, app_controller, qtbot, temp_dir):
        # 1. Force state reset
        app_controller.ui.currentView = "Library"
        model = app_controller.skillModel
        model._all_skills = []
        model._apply_filter(reset=True)

        # Setup: Add a dummy skill to the model
        skill_dir = temp_dir / "test_skill"
        skill_dir.mkdir()
        skill_file = skill_dir / "skill.md"
        skill_file.write_text("# Test Skill\nDescription here")

        skill_data = {
            "name": "Test Skill",
            "local_path": str(skill_dir),
            "project_path": str(temp_dir),
            "project_label": "Test Project",
            "category": "TestCat",
            "is_command": False,
            "is_package": False,
        }

        # 2. Configure model for maximum visibility
        model.projectFilter = ""
        model.categoryFilter = ""
        model.filterText = ""
        model.showCommands = True
        model.showStarred = True
        model.state.is_package_only = None  # Show both source and packages

        # 3. Set skills and verify
        model.setSkills([skill_data])

        # Wait for model to populate
        qtbot.waitUntil(lambda: model.rowCount() == 1, timeout=3000)

        # Select the skill
        model.setSelected(0, True)
        assert model.selectedCount == 1

        # 4. Act: Trigger deletion
        app_controller.ops.deleteSelectedSkills()

        # 5. Assert
        qtbot.waitUntil(lambda: model.rowCount() == 0, timeout=3000)
        import time

        time.sleep(0.1)

    def test_toggle_star_ui_updates_state(self, qml_engine, app_controller, qtbot, temp_dir):
        # 1. Force state reset
        app_controller.ui.currentView = "Library"
        model = app_controller.skillModel
        model._all_skills = []
        model._apply_filter(reset=True)

        # Setup
        skill_dir = temp_dir / "star_skill"
        skill_dir.mkdir()

        skill_data = {
            "name": "Star Skill",
            "local_path": str(skill_dir),
            "project_path": str(temp_dir),
            "project_label": "StarProj",
            "category": "StarCat",
            "is_starred": False,
            "is_package": False,
        }

        model.projectFilter = ""
        model.categoryFilter = ""
        model.showStarred = True
        model.state.is_package_only = None

        model.setSkills([skill_data])
        qtbot.waitUntil(lambda: model.rowCount() == 1, timeout=3000)

        # 2. Find index manually since AppController.selectSkill expects int
        index = -1
        for i in range(model.rowCount()):
            if model.data(model.index(i, 0), model.PathRole) == str(skill_dir):
                index = i
                break

        assert index != -1
        app_controller.selectSkill(index)

        # Verify selection was successful
        assert app_controller._selected_skill.get("local_path") == str(skill_dir)

        # 3. Act
        app_controller.ops.toggleStarred()

        # 4. Assert
        def check_starred():
            return model.data(model.index(0, 0), model.IsStarredRole) is True

        qtbot.waitUntil(check_starred, timeout=3000)
        assert str(skill_dir) in app_controller._starred_paths

        # Toggle back
        app_controller.ops.toggleStarred()
        qtbot.waitUntil(lambda: not check_starred(), timeout=3000)
        assert str(skill_dir) not in app_controller._starred_paths
