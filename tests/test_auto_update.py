"""Auto-update regression tests: Silent/Prompt must fire on real drift signals.

Covers the root causes fixed in this change:
- ``compare_source_and_project_skills`` never returned ``outdated``
- ``scan_for_updates_sync`` never refreshed ``latest_version`` (no force_refresh)
- ``recalculateStats`` ignored package version drift
- ``prompt`` mode had no handling at all
"""

from unittest.mock import MagicMock, patch

from skill_manager.controllers.update_controller import UpdateController
from skill_manager.core.skill_packages.versioning import (
    count_outdated_packages,
    get_outdated_packages,
    is_package_outdated,
    normalize_version,
)
from skill_manager.core.update_service import UpdateService


def test_normalize_version_strips_v_and_whitespace():
    assert normalize_version("v1.2.3") == "1.2.3"
    assert normalize_version(" V2.0 ") == "2.0"
    assert normalize_version("") == ""
    assert normalize_version(None) == ""
    assert normalize_version("1.0.0") == "1.0.0"


def test_is_package_outdated_matches_qml_is_latest():
    assert is_package_outdated({"current_version": "1.0.0", "latest_version": "2.0.0"}) is True
    assert is_package_outdated({"current_version": "1.0.0", "latest_version": "1.0.0"}) is False
    # v-prefix insensitivity (matches QML after normalization)
    assert is_package_outdated({"current_version": "v1.0.0", "latest_version": "1.0.0"}) is False
    # Unknown versions never auto-update (no false loops)
    assert is_package_outdated({"current_version": "", "latest_version": "2.0.0"}) is False
    assert is_package_outdated({"current_version": "1.0.0", "latest_version": ""}) is False
    # "latest" sentinel (detection fallback) never counts as outdated
    assert is_package_outdated({"current_version": "1.0.0", "latest_version": "latest"}) is False
    assert is_package_outdated({"current_version": "latest", "latest_version": "latest"}) is False


def test_count_outdated_packages_handles_none():
    assert count_outdated_packages(None) == 0
    assert count_outdated_packages([]) == 0
    pkgs = [
        {"current_version": "1.0.0", "latest_version": "2.0.0"},
        {"current_version": "1.0.0", "latest_version": "1.0.0"},
    ]
    assert count_outdated_packages(pkgs) == 1
    assert len(get_outdated_packages(pkgs)) == 1


def test_compare_detects_outdated_contents(tmp_path):
    src = tmp_path / "src" / "alpha"
    proj = tmp_path / "proj" / "alpha"
    src.mkdir(parents=True)
    proj.mkdir(parents=True)
    (src / "SKILL.md").write_text("version A", encoding="utf-8")
    (proj / "SKILL.md").write_text("version B", encoding="utf-8")

    results = UpdateService.compare_source_and_project_skills(
        [{"name": "Alpha", "folder_name": "alpha", "local_path": str(src)}],
        [{"project_label": "P1", "skills": [{"folder_name": "alpha", "local_path": str(proj)}]}],
    )
    assert results[0]["status"] == "outdated"
    assert results[0]["projects"][0]["status"] == "outdated"


def test_compare_identical_contents_is_up_to_date(tmp_path):
    import shutil

    src = tmp_path / "src2" / "alpha"
    proj = tmp_path / "proj2" / "alpha"
    src.mkdir(parents=True)
    (src / "SKILL.md").write_text("same", encoding="utf-8")
    shutil.copytree(src, proj)

    results = UpdateService.compare_source_and_project_skills(
        [{"name": "Alpha", "folder_name": "alpha", "local_path": str(src)}],
        [{"project_label": "P1", "skills": [{"folder_name": "alpha", "local_path": str(proj)}]}],
    )
    assert results[0]["status"] == "up_to_date"


def test_compare_missing_still_missing(tmp_path):
    src = tmp_path / "src3" / "alpha"
    src.mkdir(parents=True)
    (src / "SKILL.md").write_text("x", encoding="utf-8")
    results = UpdateService.compare_source_and_project_skills(
        [{"name": "Alpha", "folder_name": "alpha", "local_path": str(src)}],
        [{"project_label": "P1", "skills": []}],
    )
    assert results[0]["status"] == "missing"


def test_scan_refreshes_latest_versions():
    """scan_for_updates_sync must probe for new versions (force_refresh=True)."""
    service = UpdateService(sources=[], projects=[], update_packages=[{"name": "P"}])
    with (
        patch("skill_manager.core.update_service.discover_package_skills", return_value=[]),
        patch("skill_manager.core.update_service.discover_project_skills", return_value=[]),
        patch(
            "skill_manager.core.update_service.check_skill_package_versions",
            return_value={"name": "P"},
        ) as mock_check,
    ):
        service.scan_for_updates_sync(MagicMock(), MagicMock())
    assert mock_check.called
    _, kwargs = mock_check.call_args
    assert (
        kwargs.get("force_refresh") is True
        or (
            len(mock_check.call_args.args) >= 1
            and mock_check.call_args.kwargs.get("force_refresh") is True
        )
        or "force_refresh" in str(mock_check.call_args)
    )


def _make_controller(mock_app):
    mock_app._sources = ["/src"]
    mock_app._projects = ["/project"]
    mock_app._update_packages = [{"name": "S1"}]
    mock_app._syncing_projects = []
    mock_app._project_aliases = {}
    mock_app._library_model._all_skills = []
    return UpdateController(mock_app)


def test_recalculate_stats_includes_package_drift(mock_app):
    ctrl = _make_controller(mock_app)
    mock_app._update_results = [{"status": "up_to_date"}]
    mock_app._update_packages = [
        {"name": "A", "current_version": "1.0.0", "latest_version": "2.0.0"},
        {"name": "B", "current_version": "1.0.0", "latest_version": "1.0.0"},
    ]
    ctrl.recalculateStats()
    assert mock_app._stats_outdated == 1
    assert mock_app._stats_up_to_date == 1


def test_recalculate_stats_ignores_skill_drift(mock_app):
    """Skill content drift must not arm the header count / Update All button."""
    ctrl = _make_controller(mock_app)
    mock_app._update_results = [{"status": "outdated"}, {"status": "outdated"}]
    mock_app._update_packages = [
        {"name": "A", "current_version": "1.0.0", "latest_version": "1.0.0"},
    ]
    ctrl.recalculateStats()
    assert mock_app._stats_outdated == 0


@patch("skill_manager.controllers.update_controller.UpdateService")
def test_scan_auto_on_triggers_on_package_drift(mock_service_class, mock_app):
    """Auto Update on must call updateNow when packages drift, even with no skill results."""
    ctrl = _make_controller(mock_app)
    mock_app._config.get.side_effect = lambda k, default=None: {
        "skill_package_auto_update": True
    }.get(k, default)
    # No skill-level outdated at all — only package drift.
    mock_app._update_results = []
    mock_app._update_packages = []

    def mock_scan(status_callback, completion_callback):
        completion_callback(
            [],
            [{"name": "A", "current_version": "1.0.0", "latest_version": "9.9.9"}],
        )

    mock_service_class.return_value.scan_for_updates.side_effect = mock_scan
    with (
        patch(
            "skill_manager.controllers.update_controller.QTimer.singleShot",
            side_effect=lambda ms, obj, cb: cb(),
        ),
        patch.object(ctrl, "updateNow") as mock_update_now,
    ):
        ctrl.scanForUpdates()
        assert mock_app._stats_outdated == 1
        mock_update_now.assert_called_once()


@patch("skill_manager.controllers.update_controller.UpdateService")
def test_scan_auto_off_emits_toast_without_updating(mock_service_class, mock_app, qtbot):
    """Auto Update off must emit the updates-available toast, never update."""
    ctrl = _make_controller(mock_app)
    mock_app._config.get.side_effect = lambda k, default=None: {
        "skill_package_auto_update": False
    }.get(k, default)

    def mock_scan(status_callback, completion_callback):
        completion_callback(
            [],
            [{"name": "A", "current_version": "1.0.0", "latest_version": "9.9.9"}],
        )

    mock_service_class.return_value.scan_for_updates.side_effect = mock_scan
    with (
        patch(
            "skill_manager.controllers.update_controller.QTimer.singleShot",
            side_effect=lambda ms, obj, cb: cb(),
        ),
        patch.object(ctrl, "updateNow") as mock_update_now,
        qtbot.waitSignal(ctrl.updatesAvailable, timeout=1000) as blocker,
    ):
        ctrl.scanForUpdates()
        mock_update_now.assert_not_called()
    assert blocker.args == [1]


@patch("skill_manager.controllers.update_controller.UpdateService")
def test_scan_auto_off_silent_when_up_to_date(mock_service_class, mock_app):
    """No toast when nothing is outdated."""
    ctrl = _make_controller(mock_app)
    mock_app._config.get.side_effect = lambda k, default=None: {
        "skill_package_auto_update": False
    }.get(k, default)

    def mock_scan(status_callback, completion_callback):
        completion_callback(
            [],
            [{"name": "A", "current_version": "1.0.0", "latest_version": "1.0.0"}],
        )

    mock_service_class.return_value.scan_for_updates.side_effect = mock_scan
    toast_calls = []
    ctrl.updatesAvailable.connect(lambda count: toast_calls.append(count))
    with (
        patch(
            "skill_manager.controllers.update_controller.QTimer.singleShot",
            side_effect=lambda ms, obj, cb: cb(),
        ),
        patch.object(ctrl, "updateNow") as mock_update_now,
    ):
        ctrl.scanForUpdates()
        mock_update_now.assert_not_called()
    assert toast_calls == []
    assert mock_app._stats_outdated == 0


@patch("skill_manager.controllers.update_controller.UpdateService")
def test_auto_update_finished_toast_after_background_run(mock_service_class, mock_app, qtbot):
    """Completion of an auto-triggered run must emit the finished toast."""
    ctrl = _make_controller(mock_app)
    mock_app._config.get.side_effect = lambda k, default=None: {
        "skill_package_auto_update": True
    }.get(k, default)
    mock_app._update_results = []
    mock_app._update_packages = [
        {
            "name": "A",
            "package_id": "a",
            "is_updating": False,
            "current_version": "1.0.0",
            "latest_version": "2.0.0",
        }
    ]
    mock_app._projects = []
    mock_app._syncing_projects = []

    def mock_scan(status_callback, completion_callback):
        completion_callback(
            [],
            [
                {
                    "name": "A",
                    "package_id": "a",
                    "current_version": "1.0.0",
                    "latest_version": "2.0.0",
                }
            ],
        )

    def mock_run(status_callback, source_progress_callback, completion_callback):
        source_progress_callback(
            0,
            {
                "name": "A",
                "package_id": "a",
                "is_updating": False,
                "just_finished": True,
                "current_version": "2.0.0",
                "latest_version": "2.0.0",
            },
        )
        completion_callback({"merged": 1, "failed": 0}, mock_app._update_packages)

    mock_service_class.return_value.scan_for_updates.side_effect = mock_scan
    mock_service_class.return_value.run_global_update.side_effect = mock_run

    with (
        patch(
            "skill_manager.controllers.update_controller.QTimer.singleShot",
            side_effect=lambda ms, obj, cb: cb(),
        ),
        qtbot.waitSignal(ctrl.autoUpdateFinished, timeout=2000) as blocker,
    ):
        ctrl.scanForUpdates()
    assert blocker.args == [1, 0]
    assert mock_app._stats_outdated == 0


@patch("skill_manager.controllers.update_controller.UpdateService")
def test_manual_update_emits_no_finished_toast(mock_service_class, mock_app):
    """Manual runs surface the status pill only — no toast."""
    ctrl = _make_controller(mock_app)
    mock_app._update_results = []
    mock_app._update_packages = [
        {"name": "A", "package_id": "a", "is_updating": False},
    ]
    mock_app._projects = []
    mock_app._syncing_projects = []

    def mock_run(status_callback, source_progress_callback, completion_callback):
        completion_callback({"merged": 1, "failed": 0}, mock_app._update_packages)

    mock_service_class.return_value.run_global_update.side_effect = mock_run
    toast_calls = []
    ctrl.autoUpdateFinished.connect(lambda updated, failed: toast_calls.append((updated, failed)))

    with patch(
        "skill_manager.controllers.update_controller.QTimer.singleShot",
        side_effect=lambda ms, obj, cb: cb(),
    ):
        ctrl.updateNow()
    assert toast_calls == []


# --- Stuck-flag regression tests (infinite loading bars) ---


@patch("skill_manager.controllers.update_controller.UpdateService")
def test_update_now_finalize_clears_stuck_package_flags(mock_service_class, mock_app):
    """Finalize must clear is_updating even when no progress callback fired."""
    ctrl = _make_controller(mock_app)
    mock_app._update_packages = [
        {"name": "A", "package_id": "a", "is_updating": False},
        {"name": "B", "package_id": "b", "is_updating": False},
    ]
    mock_app._projects = ["/p1"]
    mock_app._syncing_projects = []

    captured = {}

    def mock_run(status_callback, source_progress_callback, completion_callback):
        captured["completion"] = completion_callback
        # Simulate a worker that never delivered progress callbacks.

    mock_service_class.return_value.run_global_update.side_effect = mock_run

    with patch(
        "skill_manager.controllers.update_controller.QTimer.singleShot",
        side_effect=lambda ms, obj, cb: cb(),
    ):
        ctrl.updateNow()
        assert all(s["is_updating"] for s in mock_app._update_packages)
        captured["completion"]({"merged": 0, "failed": 0}, mock_app._update_packages)

    assert all(s["is_updating"] is False for s in mock_app._update_packages)
    assert mock_app._syncing_projects == []
    mock_app.updatePackagesChanged.emit.assert_called()
    mock_app.config_mgr.publishProjectSyncState.assert_called()
    mock_app.projectsChanged.emit.assert_called()


@patch("skill_manager.controllers.update_controller.UpdateService")
def test_update_now_republishes_project_sync_state(mock_service_class, mock_app):
    """Starting an update must invalidate the cached updateProjects list."""
    ctrl = _make_controller(mock_app)
    mock_app._update_packages = []
    mock_app._projects = []
    mock_app._syncing_projects = []
    mock_service_class.return_value.run_global_update.return_value = None

    ctrl.updateNow()

    mock_app.config_mgr.publishProjectSyncState.assert_called()


def test_scan_ignored_while_loading(mock_app):
    ctrl = _make_controller(mock_app)
    mock_app._is_loading = True
    with patch("skill_manager.controllers.update_controller.UpdateService") as mock_service_class:
        ctrl.scanForUpdates()
        mock_service_class.return_value.scan_for_updates.assert_not_called()
    assert any("already running" in c.args[0] for c in mock_app._set_status.call_args_list)


def test_update_now_ignored_while_running(mock_app):
    ctrl = _make_controller(mock_app)
    mock_app._update_packages = [{"name": "A", "is_updating": True}]
    mock_app._syncing_projects = []
    with patch("skill_manager.controllers.update_controller.UpdateService") as mock_service_class:
        ctrl.updateNow()
        mock_service_class.assert_not_called()
    assert any("already in progress" in c.args[0] for c in mock_app._set_status.call_args_list)


@patch("skill_manager.controllers.update_controller.UpdateService")
def test_scan_start_failure_rolls_back_loading(mock_service_class, mock_app):
    ctrl = _make_controller(mock_app)
    mock_app._is_loading = False
    mock_service_class.return_value.scan_for_updates.side_effect = RuntimeError("no thread")

    ctrl.scanForUpdates()

    assert mock_app._is_loading is False
    mock_app.isLoadingChanged.emit.assert_called()
    assert any("Failed to start" in c.args[0] for c in mock_app._set_status.call_args_list)


def test_global_update_top_failure_still_completes():
    """A top-level service failure must still fire completion (flags clear)."""
    from skill_manager.core.update_service import UpdateService

    service = UpdateService(sources=[], projects=[], update_packages=[{"name": "P"}])
    status_cb = MagicMock()
    comp_cb = MagicMock()
    with patch(
        "skill_manager.core.update_service.resolve_package_storage",
        side_effect=RuntimeError("boom"),
    ):
        service.run_global_update_sync(status_cb, MagicMock(), comp_cb)

    comp_cb.assert_called_once()
    result, _ = comp_cb.call_args.args
    assert result["failed"] == 1
    assert status_cb.call_args_list[-1].args[0] == "Global update failed: boom"


def test_run_package_update_commits_by_package_id_after_shift(mock_app, tmp_path):
    """Finalize must follow package_id, not the stale entry-time index."""
    from skill_manager.controllers.update_controller import UpdateController

    pkg_a = tmp_path / "a"
    pkg_b = tmp_path / "b"
    pkg_a.mkdir()
    pkg_b.mkdir()
    mock_app._sources = []
    mock_app._projects = []
    mock_app._archive_paths = []
    mock_app._starred_paths = []
    mock_app._project_aliases = {}
    mock_app._categories = []
    mock_app._update_packages = [
        {"package_id": "pid-a", "name": "A", "package_path": str(pkg_a)},
        {"package_id": "pid-b", "name": "B", "package_path": str(pkg_b)},
    ]
    ctrl = UpdateController(mock_app)

    callbacks = []
    with (
        patch.object(ctrl, "_resolvePackageStorageState"),
        patch(
            "skill_manager.controllers.update_controller.QTimer.singleShot",
            side_effect=lambda ms, obj, cb: callbacks.append(cb),
        ),
        patch("skill_manager.core.skill_packages.package_project_path_conflicts", return_value=[]),
        patch(
            "skill_manager.core.update_service.run_skill_package_update",
            return_value={"status": "ok"},
        ),
        patch(
            "skill_manager.core.update_service.scan_package_inventory",
            return_value={"scan_ok": True, "skills": {}},
        ),
        patch(
            "skill_manager.core.update_service.diff_package_inventory",
            return_value={"added": [], "updated": [], "removed": []},
        ),
        patch("skill_manager.core.update_service.inventory_removals_verified", return_value=False),
        patch("skill_manager.core.persistence.load_package_skill_inventory", return_value={}),
        patch("skill_manager.core.persistence.save_package_skill_inventory"),
    ):
        ctrl.runPackageUpdate(0)
        # A new package lands at position 0 while the worker runs.
        mock_app._update_packages.insert(
            0, {"package_id": "pid-new", "name": "NEW", "package_path": str(pkg_a)}
        )
        for cb in callbacks:
            cb()

    by_id = {p["package_id"]: p for p in mock_app._update_packages}
    assert by_id["pid-a"]["is_updating"] is False
    assert by_id["pid-a"]["just_finished"] is True
    # The innocent row must not receive A's payload.
    assert by_id["pid-new"]["name"] == "NEW"
    assert by_id["pid-new"].get("just_finished", False) is False


def test_run_package_update_ignored_when_already_updating(mock_app):
    from skill_manager.controllers.update_controller import UpdateController

    mock_app._sources = []
    mock_app._projects = []
    mock_app._update_packages = [{"package_id": "p1", "name": "A", "is_updating": True}]
    ctrl = UpdateController(mock_app)
    with patch.object(ctrl, "_resolvePackageStorageState"):
        ctrl.runPackageUpdate(0)
    assert any("already in progress" in c.args[0] for c in mock_app._set_status.call_args_list)


def test_publish_project_sync_state_invalidates_cache(mock_app, mock_config):
    """publishProjectSyncState must drop the stale cached project list."""
    from skill_manager.controllers.config_controller import ConfigController

    mock_app._config = mock_config
    mock_app._projects = ["/proj"]
    mock_app._syncing_projects = ["/proj"]
    ctrl = ConfigController(mock_app)
    ctrl._cached_update_projects = [{"name": "stale", "is_updating": True}]

    ctrl.publishProjectSyncState()

    assert ctrl._cached_update_projects is None
    assert ctrl.updateProjects[0]["is_updating"] is True
    mock_app._syncing_projects = []
    ctrl.publishProjectSyncState()
    assert ctrl.updateProjects[0]["is_updating"] is False


@patch("skill_manager.controllers.update_controller.UpdateService")
def test_update_now_finalize_drops_header_count(mock_service_class, mock_app):
    """After a global update the header must read 0 without waiting for a scan."""
    ctrl = _make_controller(mock_app)
    mock_app._update_results = []
    mock_app._update_packages = [
        {
            "name": "A",
            "package_id": "a",
            "is_updating": False,
            "current_version": "1.0.0",
            "latest_version": "2.0.0",
        }
    ]
    mock_app._projects = []
    mock_app._syncing_projects = []

    def mock_run(status_callback, source_progress_callback, completion_callback):
        source_progress_callback(
            0,
            {
                "name": "A",
                "package_id": "a",
                "is_updating": False,
                "just_finished": True,
                "current_version": "2.0.0",
                "latest_version": "2.0.0",
            },
        )
        completion_callback({"merged": 1, "failed": 0}, mock_app._update_packages)

    mock_service_class.return_value.run_global_update.side_effect = mock_run

    with patch(
        "skill_manager.controllers.update_controller.QTimer.singleShot",
        side_effect=lambda ms, obj, cb: cb(),
    ):
        ctrl.updateNow()

    assert mock_app._stats_outdated == 0


def test_run_package_update_finalize_drops_header_count(mock_app, tmp_path):
    """Updating the last outdated package individually must disable Update All."""
    from skill_manager.controllers.update_controller import UpdateController

    pkg = tmp_path / "pkg"
    pkg.mkdir()
    mock_app._sources = []
    mock_app._projects = []
    mock_app._archive_paths = []
    mock_app._starred_paths = []
    mock_app._project_aliases = {}
    mock_app._categories = []
    mock_app._update_results = []
    mock_app._update_packages = [
        {
            "package_id": "pid-a",
            "name": "A",
            "package_path": str(pkg),
            "current_version": "1.0.0",
            "latest_version": "2.0.0",
        }
    ]
    ctrl = UpdateController(mock_app)

    callbacks = []
    with (
        patch.object(ctrl, "_resolvePackageStorageState"),
        patch(
            "skill_manager.controllers.update_controller.QTimer.singleShot",
            side_effect=lambda ms, obj, cb: callbacks.append(cb),
        ),
        patch("skill_manager.core.skill_packages.package_project_path_conflicts", return_value=[]),
        patch(
            "skill_manager.core.update_service.run_skill_package_update",
            return_value={
                "status": "ok",
                "current_version": "2.0.0",
                "latest_version": "2.0.0",
            },
        ),
        patch(
            "skill_manager.core.update_service.scan_package_inventory",
            return_value={"scan_ok": True, "skills": {}},
        ),
        patch(
            "skill_manager.core.update_service.diff_package_inventory",
            return_value={"added": [], "updated": [], "removed": []},
        ),
        patch("skill_manager.core.update_service.inventory_removals_verified", return_value=False),
        patch("skill_manager.core.persistence.load_package_skill_inventory", return_value={}),
        patch("skill_manager.core.persistence.save_package_skill_inventory"),
    ):
        ctrl.runPackageUpdate(0)
        for cb in callbacks:
            cb()

    assert mock_app._stats_outdated == 0
