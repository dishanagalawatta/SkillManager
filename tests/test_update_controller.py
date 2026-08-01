import json
from unittest.mock import MagicMock, patch

import pytest

from skill_manager.controllers.update_controller import UpdateController
from skill_manager.core.schemas import UpdatePackageRecord


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
        mock_app._set_status.assert_any_call("Update scan complete: 1 package skills processed")


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
            "skill_manager.core.update_service.run_skill_package_update"
        ) as run_skill_package_update,
    ):
        update_controller.runPackageUpdate(0)

    run_skill_package_update.assert_not_called()
    mock_app._set_status.assert_any_call(
        f"Update failed for skills: Package storage path overlaps a project skills path: {package_path}"
    )


@patch("skill_manager.controllers.update_controller.QTimer.singleShot")
@patch("skill_manager.core.discovery.DiscoveryService.discover_single")
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
@patch("skill_manager.core.discovery.DiscoveryService.discover_single")
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
            "skill_manager.core.update_service.run_skill_package_update",
            return_value={"status": "ok"},
        ),
        patch(
            "skill_manager.core.update_service.scan_package_inventory",
            return_value={"scan_ok": True, "skills": {"new_skill": {"name": "new_skill"}}},
        ),
        patch(
            "skill_manager.core.update_service.diff_package_inventory",
            return_value={"added": ["new_skill"], "updated": [], "removed": []},
        ),
        patch("skill_manager.core.update_service.inventory_removals_verified", return_value=False),
        patch("skill_manager.core.persistence.load_package_skill_inventory", return_value={}),
        patch("skill_manager.core.persistence.save_package_skill_inventory"),
        patch("skill_manager.core.persistence.patch_cache_add") as mock_patch_cache,
        patch(
            "skill_manager.core.discovery.DiscoveryService.discover_single",
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
            "skill_manager.core.update_service.run_skill_package_update",
            return_value={"status": "ok"},
        ),
        patch(
            "skill_manager.core.update_service.scan_package_inventory",
            return_value={"scan_ok": True, "skills": {"kept_skill": {"name": "kept_skill"}}},
        ),
        patch(
            "skill_manager.core.update_service.diff_package_inventory",
            return_value={"added": [], "updated": [], "removed": ["old_skill"]},
        ),
        patch("skill_manager.core.update_service.inventory_removals_verified", return_value=True),
        patch("skill_manager.core.persistence.load_package_skill_inventory", return_value={}),
        patch("skill_manager.core.persistence.save_package_skill_inventory"),
        patch("skill_manager.core.persistence.patch_cache_add"),
        patch("skill_manager.core.discovery.DiscoveryService.discover_single", return_value=None),
    ):
        update_controller.runPackageUpdate(0)

        for cb in timer_callbacks:
            cb()

        mock_app._library_model.removeSkillsByPath.assert_called_once_with(["old_skill"])
        mock_app._quick_copy_model.removeSkillsByPath.assert_called_once_with(["old_skill"])
        mock_app.loadInitialData.assert_not_called()


# --- addSkillPackage error-return + snap-to-latest tests ---


def test_add_skill_package_returns_error_when_latest_undetectable(update_controller, mock_app):
    """addSkillPackage returns a JSON error and does NOT append to state."""
    mock_app._update_packages = []

    with patch(
        "skill_manager.core.skill_packages.check_skill_package_versions",
        return_value={
            "name": "mystery-pkg",
            "source_type": "custom",
            "current_version": "",
            "latest_version": "",
            "current_version_command": "",
            "latest_version_command": "",
            "repository_url": "",
        },
    ):
        result = json.loads(
            update_controller.addSkillPackage(
                {
                    "name": "mystery-pkg",
                    "source_type": "custom",
                    "package_name": "",
                    "repository_url": "",
                    "update_command": "",
                    "current_version_command": "",
                    "latest_version_command": "",
                }
            )
        )

    assert result["ok"] is False
    assert "Could not detect latest version" in result["error"]
    assert mock_app._update_packages == []


def test_add_skill_package_snaps_current_to_latest(update_controller, mock_app):
    """addSkillPackage returns ok=True and current_version == latest_version."""
    mock_app._update_packages = []
    mock_app._config = MagicMock()

    detected = {
        "name": "caveman",
        "source_type": "npx",
        "package_name": "caveman",
        "current_version": "",
        "latest_version": "1.9.0",
        "current_version_command": "",
    }
    synced = {
        **detected,
        "current_version": "1.9.0",
    }

    with patch(
        "skill_manager.core.skill_packages.check_skill_package_versions",
        side_effect=[detected, synced],
    ):
        result = json.loads(
            update_controller.addSkillPackage(
                {
                    "name": "caveman",
                    "source_type": "npx",
                    "package_name": "caveman",
                    "repository_url": "",
                    "update_command": "",
                    "current_version_command": "",
                    "latest_version_command": "",
                }
            )
        )

    assert result["ok"] is True
    assert result["name"] == "caveman"
    assert len(mock_app._update_packages) == 1
    assert mock_app._update_packages[0]["current_version"] == "1.9.0"
    assert mock_app._update_packages[0]["latest_version"] == "1.9.0"


# --- updateUpdatePackage error-return + snap-to-latest tests ---


def test_update_update_package_returns_error_when_latest_undetectable(update_controller, mock_app):
    """updateUpdatePackage returns a JSON error and does NOT overwrite state."""
    mock_app._update_packages = [{"name": "old-pkg", "package_id": "old1", "source_type": "custom"}]

    with patch(
        "skill_manager.core.skill_packages.check_skill_package_versions",
        return_value={
            "name": "old-pkg",
            "source_type": "custom",
            "current_version": "",
            "latest_version": "",
            "current_version_command": "",
            "latest_version_command": "",
            "repository_url": "",
        },
    ):
        result = json.loads(
            update_controller.updateUpdatePackage(
                0,
                {
                    "name": "old-pkg",
                    "source_type": "custom",
                    "package_name": "",
                    "repository_url": "",
                    "update_command": "",
                    "current_version_command": "",
                    "latest_version_command": "",
                },
            )
        )

    assert result["ok"] is False
    assert "Could not detect latest version" in result["error"]
    assert mock_app._update_packages[0]["name"] == "old-pkg"


def test_update_update_package_snaps_current_to_latest(update_controller, mock_app):
    """updateUpdatePackage returns ok=True and current_version == latest_version."""
    mock_app._update_packages = [{"name": "pkg-edit", "package_id": "pe1", "source_type": "npx"}]
    mock_app._config = MagicMock()

    detected = {
        "name": "pkg-edit",
        "source_type": "npx",
        "package_name": "pkg-edit",
        "current_version": "",
        "latest_version": "3.2.1",
        "current_version_command": "",
    }
    synced = {
        **detected,
        "current_version": "3.2.1",
    }

    with patch(
        "skill_manager.core.skill_packages.check_skill_package_versions",
        side_effect=[detected, synced],
    ):
        result = json.loads(
            update_controller.updateUpdatePackage(
                0,
                {
                    "name": "pkg-edit",
                    "source_type": "npx",
                    "package_name": "pkg-edit",
                    "repository_url": "",
                    "update_command": "",
                    "current_version_command": "",
                    "latest_version_command": "",
                },
            )
        )

    assert result["ok"] is True
    assert result["name"] == "pkg-edit"
    assert len(mock_app._update_packages) == 1
    assert mock_app._update_packages[0]["current_version"] == "3.2.1"
    assert mock_app._update_packages[0]["latest_version"] == "3.2.1"


def test_update_update_package_preserves_internal_state(update_controller, mock_app):
    """updateUpdatePackage preserves is_updating, just_finished, and last_updated."""
    mock_app._update_packages = [
        {
            "name": "state-pkg",
            "package_id": "sp1",
            "source_type": "npx",
            "is_updating": True,
            "just_finished": True,
            "last_updated": "2024-01-15",
        }
    ]
    mock_app._config = MagicMock()

    detected = {
        "name": "state-pkg",
        "source_type": "npx",
        "current_version": "",
        "latest_version": "2.0.0",
        "current_version_command": "",
    }
    synced = {**detected, "current_version": "2.0.0"}

    with patch(
        "skill_manager.core.skill_packages.check_skill_package_versions",
        side_effect=[detected, synced],
    ):
        json.loads(
            update_controller.updateUpdatePackage(
                0,
                {"name": "state-pkg", "source_type": "npx", "package_name": "state-pkg"},
            )
        )

    pkg = mock_app._update_packages[0]
    assert pkg["is_updating"] is True
    assert pkg["just_finished"] is True
    assert pkg["last_updated"] == "2024-01-15"


def test_update_update_package_snaps_current_to_latest_git(update_controller, mock_app):
    """updateUpdatePackage snaps current to latest for git source when local detection fails."""
    mock_app._update_packages = [
        {
            "name": "git-pkg",
            "package_id": "gp1",
            "source_type": "git",
            "repository_url": "https://github.com/test/repo.git",
        }
    ]
    mock_app._config = MagicMock()

    # Phase 1: detect — no local clone (empty current), valid latest
    detected = {
        "name": "git-pkg",
        "source_type": "git",
        "current_version": "",
        "latest_version": "2.5.0",
        "current_version_command": "",
        "repository_url": "https://github.com/test/repo.git",
    }
    # Phase 2: snap — current still empty (no local clone), latest detected
    synced = {**detected, "current_version": "2.5.0"}

    with patch(
        "skill_manager.core.skill_packages.check_skill_package_versions",
        side_effect=[detected, synced],
    ):
        result = json.loads(
            update_controller.updateUpdatePackage(
                0,
                {
                    "name": "git-pkg",
                    "source_type": "git",
                    "repository_url": "https://github.com/test/repo.git",
                    "package_name": "",
                    "package_path": "",
                    "update_command": "",
                    "current_version_command": "",
                    "latest_version_command": "",
                },
            )
        )

    assert result["ok"] is True
    assert result["name"] == "git-pkg"
    assert mock_app._update_packages[0]["current_version"] == "2.5.0"
    assert mock_app._update_packages[0]["latest_version"] == "2.5.0"


# ── SDET contract (merged from test_update_sdet.py; duplicates pruned) ──


def test_add_update_package_basic_validation(update_controller, mock_app):
    mock_app._update_packages = []
    # Happy path
    update_controller.addUpdatePackage("test-package")
    assert len(mock_app._update_packages) == 1
    record = UpdatePackageRecord.model_validate(mock_app._update_packages[0])
    assert record.name == "test-package"
    assert record.source_type == "npx"

    # Empty name should early return
    mock_app._update_packages = []
    update_controller.addUpdatePackage("")
    assert len(mock_app._update_packages) == 0


def test_add_skill_package_strict_schema(update_controller, mock_app):
    mock_app._update_packages = []
    data = {
        "name": "My Git Package",
        "source_type": "git",
        "package_id": "my-git",
        "repository_url": "https://github.com/test/repo.git",
        "github_token": "ghp_secret",
        "extra_field": "should-be-ignored",
    }

    with (
        patch(
            "skill_manager.core.skill_packages.check_skill_package_versions",
            side_effect=lambda x, **kw: {
                **x,
                "latest_version": x.get("latest_version") or "1.0.0",
            },
        ),
        patch.object(update_controller, "_resolvePackageStorageState"),
    ):
        update_controller.addSkillPackage(data)

    assert len(mock_app._update_packages) == 1
    record = mock_app._update_packages[0]
    assert record["name"] == "My Git Package"
    assert "extra_field" not in record
    assert record["is_updating"] is False
    assert record["last_updated"] == "Never"
    # Config fields must survive the round-trip (ADR-0008 regression)
    assert record["repository_url"] == "https://github.com/test/repo.git"
    assert record["github_token"] == "ghp_secret"


def test_update_update_package_persistence(update_controller, mock_app):
    mock_app._update_packages = [{"name": "Old", "package_id": "p1", "source_type": "npx"}]

    new_data = {"name": "New", "package_id": "p1", "source_type": "npx"}

    detected = {
        "name": "New",
        "package_id": "p1",
        "source_type": "npx",
        "latest_version": "2.0.0",
        "current_version": "",
    }
    synced = {**detected, "current_version": "2.0.0"}

    with (
        patch(
            "skill_manager.core.skill_packages.check_skill_package_versions",
            side_effect=[detected, synced],
        ),
        patch.object(update_controller, "_resolvePackageStorageState"),
    ):
        update_controller.updateUpdatePackage(0, new_data)

    assert mock_app._update_packages[0]["name"] == "New"
    assert mock_app._update_packages[0]["source_type"] == "npx"


def test_resolve_package_storage_state_recovery(update_controller, mock_app):
    # Simulate corrupted config data
    mock_app._update_packages = [
        {"name": "Valid", "package_id": "v1"},
        {"name": None},  # This will trigger coercion/validation
    ]

    with patch(
        "skill_manager.core.skill_packages.resolve_package_storage", side_effect=lambda p, i: p
    ):
        update_controller._resolvePackageStorageState()

    assert len(mock_app._update_packages) == 2
    assert mock_app._update_packages[1]["name"] == ""  # Coerced to empty string


@patch("skill_manager.controllers.update_controller.UpdateService")
def test_scan_for_updates_silent_auto_trigger(mock_service_class, update_controller, mock_app):
    mock_service = mock_service_class.return_value
    mock_app._config.get.side_effect = lambda k, default=None: {
        "skill_package_auto_update_mode": "silent",
    }.get(k, default)

    # Mock completion callback logic with an outdated result
    def mock_scan(status_callback, completion_callback):
        completion_callback([{"status": "outdated"}], [])

    mock_service.scan_for_updates.side_effect = mock_scan

    with (
        patch(
            "skill_manager.controllers.update_controller.QTimer.singleShot",
            side_effect=lambda ms, obj, cb: cb(),
        ),
        patch.object(update_controller, "updateNow") as mock_update_now,
    ):
        update_controller.scanForUpdates()
        # recalculateStats should have set stats_outdated = 1
        assert mock_app._stats_outdated == 1
        mock_update_now.assert_called_once()


def test_remove_update_package(update_controller, mock_app):
    mock_app._update_packages = [{"name": "To Remove"}]
    update_controller.removeUpdatePackage(0)
    assert len(mock_app._update_packages) == 0
    mock_app.updatePackagesChanged.emit.assert_called()


def test_update_update_package_logs_version_check(update_controller, mock_app):
    """updateUpdatePackage must log version check details."""
    mock_app._update_packages = [
        {"name": "TestPkg", "package_id": "test12345", "source_type": "git"}
    ]

    def mock_check(source, force_refresh=False, sync_current_to_latest=False):
        return {**source, "current_version": "v1.0.0", "latest_version": "v2.0.0"}

    with (
        patch(
            "skill_manager.core.skill_packages.check_skill_package_versions",
            side_effect=mock_check,
        ),
        patch.object(update_controller, "_resolvePackageStorageState"),
    ):
        update_controller.updateUpdatePackage(0, {"name": "TestPkg", "package_id": "test12345"})

    # Verify status message includes version check details
    status_call = mock_app._set_status.call_args[0][0]
    assert "Package settings saved: TestPkg" in status_call
    assert "v1.0.0" in status_call
    assert "v2.0.0" in status_call


def test_update_update_package_diagnostic_event(update_controller, mock_app):
    """updateUpdatePackage must emit a diagnostic log event with full context."""
    mock_app._update_packages = [
        {
            "name": "DiagPkg",
            "package_id": "diag12345",
            "source_type": "git",
            "repository_url": "https://github.com/test/repo.git",
        }
    ]

    def mock_check(source, force_refresh=False, sync_current_to_latest=False):
        return {**source, "current_version": "v1.0.0", "latest_version": "v2.0.0"}

    with (
        patch(
            "skill_manager.core.skill_packages.check_skill_package_versions",
            side_effect=mock_check,
        ),
        patch.object(update_controller, "_resolvePackageStorageState"),
        patch("skill_manager.core.diagnostics.get_diagnostic_logger") as mock_diag,
    ):
        update_controller.updateUpdatePackage(
            0,
            {
                "name": "DiagPkg",
                "package_id": "diag12345",
                "source_type": "git",
                "repository_url": "https://github.com/test/repo.git",
            },
        )

        # Verify diagnostic event was logged
        mock_diag.return_value.log_event.assert_called_once()
        call_args = mock_diag.return_value.log_event.call_args
        assert call_args[0][0] == "INFO"
        assert call_args[0][1] == "update_result"
        assert "Config saved for package: DiagPkg" in call_args[0][2]
        # Verify data includes all expected fields
        data = call_args[1]["data"]
        assert data["package_id"] == "diag12345"
        assert data["source_type"] == "git"
        assert data["current_version"] == "v1.0.0"
        assert data["latest_version"] == "v2.0.0"
        assert data["repository_url"] == "https://github.com/test/repo.git"
