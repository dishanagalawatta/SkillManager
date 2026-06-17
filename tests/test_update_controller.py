from unittest.mock import patch

import pytest

from skill_manager.controllers.update_controller import UpdateController


@pytest.fixture
def update_controller(mock_app):
    # Initialize mock_app with specific values needed for update controller
    mock_app._sources = ["/src"]
    app_projects = ["/project"]
    mock_app._projects = app_projects
    mock_app._update_packages = [{"name": "Source1", "is_updating": False, "just_finished": False}]
    mock_app._syncing_projects = []
    mock_app._project_aliases = {}
    mock_app._library_model._all_skills = []
    # override getProjectLabel for this test if needed, but conftest already has a generic one
    mock_app.getProjectLabel.side_effect = lambda t: "ProjectLabel" if t == "/project" else t
    return UpdateController(mock_app)


@patch("skill_manager.controllers.update_controller.UpdateService")
def test_update_now(mock_service_class, update_controller, mock_app):
    mock_service = mock_service_class.return_value
    update_controller.updateNow()

    # Verify status and state changes
    mock_app._set_status.assert_called_with("Starting global update...")
    assert "/project" in mock_app._syncing_projects
    assert mock_app._update_packages[0]["is_updating"] is True
    mock_app.projectsChanged.emit.assert_called()
    mock_app.updatePackagesChanged.emit.assert_called()

    # Verify service call
    mock_service.run_global_update.assert_called_once()

    # Test completion callback
    args, kwargs = mock_service.run_global_update.call_args
    completion_callback = kwargs["completion_callback"]

    with patch("skill_manager.controllers.update_controller.QTimer.singleShot") as mock_timer:
        completion_callback({"merged": 1, "failed": 0}, mock_app._update_packages)
        # Extract and run the inner finalize function
        timer_args = mock_timer.call_args_list[0][0]
        finalize_func = timer_args[2]
        finalize_func()

        mock_app.loadInitialData.assert_called_once()
        mock_app._set_status.assert_any_call("Global update complete: 1 updated, 0 failed")
        assert mock_app._syncing_projects == []


@patch("skill_manager.controllers.update_controller.UpdateService")
def test_scan_for_updates(mock_service_class, update_controller, mock_app):
    mock_service = mock_service_class.return_value
    update_controller.scanForUpdates()

    mock_app._set_status.assert_called_with("Scanning for updates...")
    assert mock_app._is_loading is True

    # Test completion callback
    args, kwargs = mock_service.scan_for_updates.call_args
    completion_callback = kwargs["completion_callback"]

    with patch("skill_manager.controllers.update_controller.QTimer.singleShot") as mock_timer:
        completion_callback([{"status": "up_to_date"}], mock_app._update_packages)
        finalize_func = mock_timer.call_args[0][2]
        finalize_func()

        assert mock_app._is_loading is False
        mock_app.isLoadingChanged.emit.assert_called()
        mock_app._set_status.assert_any_call("Scan complete: 1 skills processed")


def test_update_skill_in_project_success(update_controller, mock_app):
    mock_app._library_model._all_skills = [
        {"is_source": True, "name": "Skill1", "local_path": "/p1"}
    ]
    mock_app._projects = ["/project"]

    with (
        patch("skill_manager.core.copier.copy_skill_folders_to_projects") as mock_copy,
        patch(
            "skill_manager.controllers.update_controller.schedule_on_ui_thread"
        ) as schedule_on_ui_thread,
    ):
        schedule_on_ui_thread.side_effect = lambda _receiver, callback, *, delay_ms=0: (
            callback() if delay_ms == 0 else None
        )
        mock_copy.return_value = {"failed": 0}

        update_controller.updateSkillInProject("Skill1", "ProjectLabel")

        mock_copy.assert_called_once()
        delays = [call.kwargs.get("delay_ms", 0) for call in schedule_on_ui_thread.call_args_list]
        assert delays == [0, 500]


def test_run_package_update_skips_project_root_conflict(update_controller, mock_app, tmp_path):
    project_root = tmp_path / "repo"
    package_path = project_root / ".agents" / "skills"
    package_path.mkdir(parents=True)
    mock_app._projects = [str(project_root)]
    mock_app._update_packages = [
        {
            "package_id": "skills",
            "name": "skills",
            "package_path": str(package_path),
            "resolved_package_path": str(package_path),
        }
    ]

    with (
        patch(
            "skill_manager.controllers.update_controller.load_package_skill_inventory",
            return_value={},
            create=True,
        ),
        patch("skill_manager.core.persistence.load_package_skill_inventory", return_value={}),
        patch(
            "skill_manager.controllers.update_controller.QTimer.singleShot",
            side_effect=lambda _ms, _receiver, callback: callback(),
        ),
        patch(
            "skill_manager.core.skill_packages.run_skill_package_update"
        ) as run_skill_package_update,
    ):
        update_controller.runPackageUpdate(0)

    run_skill_package_update.assert_not_called()
    mock_app._set_status.assert_any_call(
        f"Update failed for skills: Package storage path overlaps a project skills path: {package_path}"
    )


@patch("skill_manager.controllers.update_controller.QTimer.singleShot")
@patch("skill_manager.core.discovery.DiscoveryService.discover_single_skill")
@patch("skill_manager.core.copier.copy_skill_folders_to_projects")
@patch("skill_manager.core.persistence.patch_cache_add")
@patch("skill_manager.core.quick_copy.discover_package_skills")
def test_sync_project_emits_categories_changed(
    mock_discover_pkg,
    mock_patch_cache,
    mock_copy,
    mock_discover_single,
    mock_timer,
    update_controller,
    mock_app,
):
    mock_app._categories = []
    mock_discover_pkg.return_value = [{"local_path": "/src/s1"}]
    mock_copy.return_value = {
        "merged": 1,
        "failed": 0,
        "details": [{"status": "merged", "message": "/project/S1.md", "project": "/project"}],
    }
    mock_discover_single.return_value = {
        "local_path": "/project/S1",
        "name": "S1",
        "category": "NewCategory",
        "project_label": "ProjectLabel",
    }

    timer_callbacks = []

    def mock_single_shot(ms, obj, callback):
        timer_callbacks.append(callback)

    mock_timer.side_effect = mock_single_shot

    update_controller.syncProject("/project")

    for cb in timer_callbacks:
        cb()

    assert "NewCategory" in mock_app._categories
    mock_app.categoriesChanged.emit.assert_called()


@patch("skill_manager.controllers.update_controller.QTimer.singleShot")
@patch("skill_manager.core.discovery.DiscoveryService.discover_single_skill")
@patch("skill_manager.core.copier.copy_skill_folders_to_projects")
@patch("skill_manager.core.persistence.patch_cache_add")
@patch("skill_manager.core.quick_copy.discover_package_skills")
def test_sync_project_skips_categories_changed_when_no_new_cats(
    mock_discover_pkg,
    mock_patch_cache,
    mock_copy,
    mock_discover_single,
    mock_timer,
    update_controller,
    mock_app,
):
    mock_app._categories = ["Dev", "General"]
    mock_discover_pkg.return_value = [{"local_path": "/src/s1"}]
    mock_copy.return_value = {
        "merged": 1,
        "failed": 0,
        "details": [{"status": "merged", "message": "/project/S1.md", "project": "/project"}],
    }
    mock_discover_single.return_value = {
        "local_path": "/project/S1",
        "name": "S1",
        "category": "Dev",
        "project_label": "ProjectLabel",
    }

    timer_callbacks = []

    def mock_single_shot(ms, obj, callback):
        timer_callbacks.append(callback)

    mock_timer.side_effect = mock_single_shot

    update_controller.syncProject("/project")

    for cb in timer_callbacks:
        cb()

    assert mock_app._categories == ["Dev", "General"]


def test_recalculate_stats(update_controller, mock_app):
    mock_app._update_results = [
        {"status": "up_to_date"},
        {"status": "outdated"},
        {"status": "missing"},
        {"status": "outdated"},
    ]
    update_controller.recalculateStats()

    assert mock_app._stats_up_to_date == 1
    assert mock_app._stats_outdated == 2
    assert mock_app._stats_missing == 1
    mock_app.statsChanged.emit.assert_called_once()


def test_run_package_update_targeted_refresh(update_controller, mock_app, tmp_path):
    pkg_path = tmp_path / "pkg"
    pkg_path.mkdir()
    skill_dir = pkg_path / "new_skill"
    skill_dir.mkdir()

    mock_app._update_packages = [
        {
            "package_id": "test-pkg",
            "name": "Test Package",
            "package_path": str(pkg_path),
            "resolved_package_path": str(pkg_path),
            "is_updating": False,
            "just_finished": False,
        }
    ]
    mock_app._sources = []
    mock_app._projects = []
    mock_app._archive_paths = []
    mock_app._starred_paths = []
    mock_app._project_aliases = {}
    mock_app._categories = []

    mock_skill = {
        "local_path": str(skill_dir),
        "name": "new_skill",
        "category": "NewCat",
    }

    timer_callbacks = []

    def mock_single_shot(ms, obj, callback):
        timer_callbacks.append(callback)

    with (
        patch.object(update_controller, "_resolvePackageStorageState"),
        patch(
            "skill_manager.controllers.update_controller.QTimer.singleShot",
            side_effect=mock_single_shot,
        ),
        patch("skill_manager.core.skill_packages.package_project_path_conflicts", return_value=[]),
        patch(
            "skill_manager.core.skill_packages.run_skill_package_update",
            return_value={"status": "ok"},
        ),
        patch(
            "skill_manager.core.skill_packages.scan_package_inventory",
            return_value={"scan_ok": True, "skills": {"new_skill": {"name": "new_skill"}}},
        ),
        patch(
            "skill_manager.core.skill_packages.diff_package_inventory",
            return_value={"added": ["new_skill"], "updated": [], "removed": []},
        ),
        patch("skill_manager.core.skill_packages.inventory_removals_verified", return_value=False),
        patch("skill_manager.core.persistence.load_package_skill_inventory", return_value={}),
        patch("skill_manager.core.persistence.save_package_skill_inventory"),
        patch("skill_manager.core.persistence.patch_cache_add") as mock_patch_cache,
        patch(
            "skill_manager.core.discovery.DiscoveryService.discover_single_skill",
            return_value=mock_skill,
        ) as mock_discover_single,
    ):
        update_controller.runPackageUpdate(0)

        for cb in timer_callbacks:
            cb()

        mock_discover_single.assert_called_once()
        mock_patch_cache.assert_called_once()
        mock_app._library_model.addOrUpdateSkills.assert_called_once_with([mock_skill])
        mock_app._quick_copy_model.addOrUpdateSkills.assert_called_once_with([mock_skill])
        mock_app.loadInitialData.assert_not_called()
        assert "NewCat" in mock_app._categories
        mock_app.categoriesChanged.emit.assert_called()


def test_run_package_update_removes_old_skills(update_controller, mock_app, tmp_path):
    pkg_path = tmp_path / "pkg"
    pkg_path.mkdir()
    kept_dir = pkg_path / "kept_skill"
    kept_dir.mkdir()

    mock_app._update_packages = [
        {
            "package_id": "test-pkg",
            "name": "Test Package",
            "package_path": str(pkg_path),
            "resolved_package_path": str(pkg_path),
            "is_updating": False,
            "just_finished": False,
        }
    ]
    mock_app._sources = []
    mock_app._projects = []
    mock_app._archive_paths = []
    mock_app._starred_paths = []
    mock_app._project_aliases = {}
    mock_app._categories = []

    timer_callbacks = []

    def mock_single_shot(ms, obj, callback):
        timer_callbacks.append(callback)

    with (
        patch.object(update_controller, "_resolvePackageStorageState"),
        patch(
            "skill_manager.controllers.update_controller.QTimer.singleShot",
            side_effect=mock_single_shot,
        ),
        patch("skill_manager.core.skill_packages.package_project_path_conflicts", return_value=[]),
        patch(
            "skill_manager.core.skill_packages.run_skill_package_update",
            return_value={"status": "ok"},
        ),
        patch(
            "skill_manager.core.skill_packages.scan_package_inventory",
            return_value={"scan_ok": True, "skills": {"kept_skill": {"name": "kept_skill"}}},
        ),
        patch(
            "skill_manager.core.skill_packages.diff_package_inventory",
            return_value={"added": [], "updated": [], "removed": ["old_skill"]},
        ),
        patch("skill_manager.core.skill_packages.inventory_removals_verified", return_value=True),
        patch("skill_manager.core.persistence.load_package_skill_inventory", return_value={}),
        patch("skill_manager.core.persistence.save_package_skill_inventory"),
        patch("skill_manager.core.persistence.patch_cache_add"),
        patch(
            "skill_manager.core.discovery.DiscoveryService.discover_single_skill", return_value=None
        ),
    ):
        update_controller.runPackageUpdate(0)

        for cb in timer_callbacks:
            cb()

        mock_app._library_model.removeSkillsByPath.assert_called_once_with(["old_skill"])
        mock_app._quick_copy_model.removeSkillsByPath.assert_called_once_with(["old_skill"])
        mock_app.loadInitialData.assert_not_called()
