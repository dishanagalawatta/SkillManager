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
            config_mgr.skillPackageAutoUpdateMode = "silent"
        assert app_controller._config.get("skill_package_auto_update_mode") == "silent"

    def test_add_source_project_ui_flow(self, qml_engine, app_controller, qtbot, tmp_path):
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
        test_proj_dir = tmp_path / "test_project"
        skills_dir = test_proj_dir / ".agents" / "skills"
        skills_dir.mkdir(parents=True)
        test_project = str(test_proj_dir)

        with qtbot.waitSignal(app_controller.projectsChanged, timeout=1000):
            config_mgr.addProject(test_project)

        expected_project = str(skills_dir.resolve())
        assert any(expected_project == p for p in app_controller._projects)

    def test_project_alias_ui_update(self, qml_engine, app_controller, qtbot, clean_models):
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

    def test_add_project_auto_discovers_and_links_preexisting_skill(
        self, qml_engine, app_controller, qtbot, tmp_path
    ):
        """Adding a project folder auto-discovers pre-existing skills and
        links exact matches to package skills — no manual refresh needed."""
        from skill_manager.core.persistence import load_project_skill_ownership
        from skill_manager.core.update_service import UpdateService

        # 1. Package source with skill "alpha"
        content = "---\nname: alpha\n---\n# Alpha skill\n"
        source_dir = tmp_path / "package_source"
        alpha_src = source_dir / "alpha"
        alpha_src.mkdir(parents=True)
        (alpha_src / "SKILL.md").write_text(content, encoding="utf-8")
        with qtbot.waitSignal(app_controller.sourcesChanged, timeout=1000):
            app_controller.config_mgr.addSource(str(source_dir))

        # Simulate a registered package for the added source, restoring
        # the session-scoped app's original state afterwards.
        original_packages = app_controller._update_packages
        app_controller._update_packages = [
            {"name": "Test Pkg", "package_id": "pkg-1", "package_path": str(source_dir)}
        ]

        # 2. Project with a PRE-EXISTING identical skill
        proj_dir = tmp_path / "project"
        skills_dir = proj_dir / ".agents" / "skills"
        alpha_proj = skills_dir / "alpha"
        alpha_proj.mkdir(parents=True)
        (alpha_proj / "SKILL.md").write_text(content, encoding="utf-8")

        try:
            with qtbot.waitSignal(app_controller.projectsChanged, timeout=1000):
                app_controller.config_mgr.addProject(str(proj_dir))

            # 3. Discovery refresh ran synchronously (SynchronousTaskRunner):
            #    the pre-existing skill is in the library model without a
            #    manual refresh.
            names = {
                getattr(skill, "name", None) for skill in app_controller.libraryModel._all_skills
            }
            assert "alpha" in names
            assert any(
                not getattr(skill, "is_package", False) and getattr(skill, "name", None) == "alpha"
                for skill in app_controller.libraryModel._all_skills
            )

            # 4. Ownership linked to the package
            ownership = load_project_skill_ownership()
            project_key = UpdateService.ownership_project_key(str(skills_dir.resolve()))
            assert ownership.get(project_key, {}).get("alpha") == "pkg-1"
        finally:
            app_controller._update_packages = original_packages
