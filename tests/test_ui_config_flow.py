from pathlib import Path

import pytest


@pytest.mark.usefixtures("setup_qml_style")
class TestUIConfigFlow:
    def test_settings_propagation(self, qml_engine, app_controller, qtbot):
        """Verify that UI-driven config changes propagate to the persistence layer."""
        config_mgr = app_controller.config_mgr

        # 1. Test numeric validation propagation
        with qtbot.waitSignal(config_mgr.scrollSpeedMultiplierChanged, timeout=1000):
            config_mgr.scrollSpeedMultiplier = 2.5
        assert app_controller._config.get("scroll_speed_multiplier") == 2.5

        # 2. Test string mode propagation
        with qtbot.waitSignal(config_mgr.skillPackageAutoUpdateModeChanged, timeout=1000):
            config_mgr.skillPackageAutoUpdateMode = "auto"
        assert app_controller._config.get("skill_package_auto_update_mode") == "auto"

    def test_add_source_project_ui_flow(self, qml_engine, app_controller, qtbot):
        """Verify adding sources and projects via UI slots."""
        config_mgr = app_controller.config_mgr

        # 1. Add Source
        test_source = "/path/test/source"
        with qtbot.waitSignal(app_controller.sourcesChanged, timeout=1000):
            config_mgr.addSource(test_source)

        # Normalize for comparison
        expected_source = str(Path(test_source).resolve())
        assert any(expected_source == s for s in app_controller._sources)

        # 2. Add Project
        test_project = "/path/test/project"
        with qtbot.waitSignal(app_controller.projectsChanged, timeout=1000):
            config_mgr.addProject(test_project)

        expected_project = str(Path(test_project).resolve())
        assert any(expected_project == p for p in app_controller._projects)

    def test_project_alias_ui_update(self, qml_engine, app_controller, qtbot):
        """Verify that renaming a project updates the model labels."""
        config_mgr = app_controller.config_mgr

        # 1. Setup initial project and skill
        proj_path = "/path/p1"
        app_controller._projects = [proj_path]
        app_controller.libraryModel.setSkills(
            [
                {
                    "name": "Skill 1",
                    "project_path": proj_path,
                    "project_label": "p1",
                    "is_package": True,
                }
            ]
        )

        # 2. Set Alias
        with qtbot.waitSignal(config_mgr.updateProjectsChanged, timeout=1000):
            config_mgr.setProjectAlias(proj_path, "Cool Project")

        # 3. Verify labels in model updated
        names = [
            app_controller.libraryModel.data(
                app_controller.libraryModel.index(0, 0), app_controller.libraryModel.ProjectRole
            )
        ]
        assert "Cool Project" in names
        assert config_mgr.getProjectLabel(proj_path) == "Cool Project"

    def test_shortcut_recording_toggle(self, qml_engine, app_controller, qtbot):
        """Verify the shortcut recording state toggle."""
        config_mgr = app_controller.config_mgr

        assert config_mgr.isRecordingShortcut is False

        with qtbot.waitSignal(config_mgr.isRecordingShortcutChanged, timeout=1000):
            config_mgr.isRecordingShortcut = True

        assert config_mgr.isRecordingShortcut is True
