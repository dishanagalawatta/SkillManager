"""Regression tests for the skill-package update workflow.

Covers the guarantees added for the "sometimes updates are not working"
report:

* **WS1** every remote probe is bounded and non-interactive, and a probe that
  fails is reported as a failure instead of looking like "up to date".
* **WS2** a scan can never leave the app stuck in the loading state, and a
  failed scan is never reported as "Update scan complete: 0".
* **WS3** no package record, config write, or storage cleanup can silently
  lose data.
* **WS4** a package whose remote could not be reached is reported as such and
  can be retried, instead of being presented as up to date.
* **WS5** one remote is probed once per scan, not once per call site, and
  full filesystem rescans are coalesced.
"""

import json
import os
from unittest.mock import MagicMock, patch

import orjson
import pytest

from skill_manager.controllers.update_controller import UpdateController
from skill_manager.core.schemas import UpdatePackageRecord
from skill_manager.core.skill_packages.versioning import (
    RemoteProbeCache,
    VersionProbe,
    check_skill_package_versions,
    count_unchecked_packages,
    get_git_tag,
    probe_git_remote_version,
)
from skill_manager.core.update_service import UpdateService

# --------------------------------------------------------------------------
# WS1 — bounded, non-interactive probes
# --------------------------------------------------------------------------


@patch("skill_manager.core.skill_packages.versioning.cmd.Git")
def test_probe_bounds_and_deinteractivates_git(mock_git):
    """The probe must bound the git call and use a non-interactive env.

    Regression guard: the previous implementation built an ``env`` dict and
    then never passed it to ``execute``, and had no timeout at all — so a
    credential-gated remote blocked the scan thread forever.

    The bound is expressed differently per platform: GitPython's
    ``kill_after_timeout`` is not supported on Windows (it raises), so
    there the deadline is enforced by killing the process ourselves.
    """
    mock_git.return_value.execute.return_value = "h\trefs/tags/v1.0.0\n"

    probe = probe_git_remote_version("https://github.com/o/r", timeout=7.5)

    assert probe == VersionProbe(version="v1.0.0", ok=True)
    _, kwargs = mock_git.return_value.execute.call_args
    if os.name == "nt":
        # The Windows branch drives the process itself.
        assert kwargs.get("as_process") is True
    else:
        assert kwargs["kill_after_timeout"] == 7.5
    assert kwargs["env"]["GIT_TERMINAL_PROMPT"] == "0"


@patch("skill_manager.core.skill_packages.versioning.cmd.Git")
def test_probe_reports_timeout_reason(mock_git):
    mock_git.return_value.execute.side_effect = Exception("killed after 7s timeout")

    probe = probe_git_remote_version("https://github.com/o/r", timeout=7.0)

    assert probe.ok is False
    assert probe.version == ""
    assert "timed out" in probe.reason


@patch("skill_manager.core.skill_packages.versioning.cmd.Git")
def test_probe_reports_unreachable_reason(mock_git):
    mock_git.return_value.execute.side_effect = Exception("could not read Username")

    probe = probe_git_remote_version("https://github.com/o/r")

    assert probe.ok is False
    assert "unreachable" in probe.reason


def test_probe_empty_url_is_not_ok():
    probe = probe_git_remote_version("")
    assert probe.ok is False
    assert probe.version == ""


@patch("skill_manager.core.skill_packages.versioning.cmd.Git")
def test_probe_keeps_truthiness_of_old_string_api(mock_git):
    """``VersionProbe`` must stay falsy when empty so ``if tag:`` keeps working."""
    mock_git.return_value.execute.side_effect = Exception("nope")
    assert not probe_git_remote_version("https://github.com/o/r")

    mock_git.return_value.execute.side_effect = None
    mock_git.return_value.execute.return_value = "h\trefs/tags/v2.0.0\n"
    assert probe_git_remote_version("https://github.com/o/r")


@patch("skill_manager.core.skill_packages.versioning.cmd.Git")
def test_get_git_tag_contract_unchanged(mock_git):
    """Existing callers still get a plain ``str``."""
    mock_git.return_value.execute.return_value = "h\trefs/tags/v9.9.9\n"
    assert get_git_tag("https://github.com/o/r", is_remote=True) == "v9.9.9"


@patch("skill_manager.core.skill_packages.versioning.cmd.Git")
def test_get_git_tag_remote_failure_is_empty_string(mock_git):
    mock_git.return_value.execute.side_effect = Exception("Network Error")
    assert get_git_tag("https://github.com/o/r", is_remote=True) == ""


# --------------------------------------------------------------------------
# WS5 — one probe per remote per scan
# --------------------------------------------------------------------------


@patch("skill_manager.core.skill_packages.versioning.get_git_tag")
def test_probe_cache_dedupes_per_url_and_token(mock_tag):
    mock_tag.return_value = "v1.0.0"
    cache = RemoteProbeCache()

    assert cache.git_tag("https://github.com/o/r", "") == "v1.0.0"
    assert cache.git_tag("https://github.com/o/r", "") == "v1.0.0"
    # A different token is a different remote identity -> re-probe.
    assert cache.git_tag("https://github.com/o/r", "tok") == "v1.0.0"

    assert mock_tag.call_count == 2
    assert cache.failure_reason() == ""


@patch("skill_manager.core.skill_packages.versioning.get_git_tag")
def test_probe_cache_exposes_failure_reason(mock_tag):
    mock_tag.return_value = ""
    cache = RemoteProbeCache()

    assert cache.probe("https://github.com/o/r").ok is False
    assert cache.attempted is True
    assert cache.failure_reason()


def test_probe_cache_not_attempted_when_unused():
    assert RemoteProbeCache().attempted is False


@patch("skill_manager.core.skill_packages.versioning.get_git_tag")
def test_shared_cache_halves_probes_across_packages(mock_tag):
    """Two identically hosted packages must cost one probe, not two."""
    mock_tag.return_value = "v1.0.0"
    cache = RemoteProbeCache()

    for name in ("A", "B"):
        check_skill_package_versions(
            {
                "name": name,
                "source_type": "git",
                "repository_url": "https://github.com/o/r.git",
            },
            force_refresh=True,
            remote_cache=cache,
        )

    assert mock_tag.call_count == 1


# --------------------------------------------------------------------------
# WS1/WS4 — a failed check is reported, never hidden
# --------------------------------------------------------------------------


@patch("skill_manager.core.skill_packages.versioning.get_git_tag")
def test_failed_probe_is_reported_not_hidden(mock_tag):
    """An unreachable remote must not look like "up to date"."""
    mock_tag.return_value = ""
    source = {
        "source_type": "git",
        "repository_url": "https://github.com/o/r.git",
        "current_version": "1.0.0",
        "latest_version": "1.0.0",
    }

    updated = check_skill_package_versions(source, force_refresh=True)

    assert updated["check_status"] == "failed"
    assert updated["check_error"]
    assert updated["last_checked_at"]
    # The stale value is kept rather than cleared — but it is flagged.
    assert updated["latest_version"] == "1.0.0"


@patch("skill_manager.core.skill_packages.versioning.get_git_tag")
def test_successful_probe_records_ok(mock_tag):
    mock_tag.return_value = "v2.0.0"
    source = {"source_type": "git", "repository_url": "https://github.com/o/r.git"}

    updated = check_skill_package_versions(source, force_refresh=True)

    assert updated["check_status"] == "ok"
    assert updated["check_error"] == ""
    assert updated["latest_version"] == "2.0.0"
    assert updated["last_checked_at"]


@patch("skill_manager.core.skill_packages.versioning.get_git_tag")
def test_non_github_host_is_probed(mock_tag):
    """Self-hosted and other hosts used to be skipped entirely."""
    mock_tag.return_value = "v3.0.0"
    source = {
        "source_type": "git",
        "repository_url": "https://git.example.com/team/repo.git",
        "current_version": "1.0.0",
    }

    updated = check_skill_package_versions(source, force_refresh=True)

    assert updated["latest_version"] == "3.0.0"
    called_urls = [call.args[0] for call in mock_tag.call_args_list]
    assert "https://git.example.com/team/repo.git" in called_urls


def test_no_version_anywhere_is_never_checked():
    updated = check_skill_package_versions({"source_type": "custom", "name": "Nothing"})
    assert updated["check_status"] == "never_checked"
    assert updated["check_error"] == ""


# --------------------------------------------------------------------------
# WS2 — the app can never be wedged by a scan
# --------------------------------------------------------------------------


@pytest.fixture
def ctrl(mock_app):
    mock_app._sources = []
    mock_app._projects = []
    mock_app._update_packages = []
    mock_app._syncing_projects = []
    mock_app._project_aliases = {}
    mock_app._library_model._all_skills = []
    mock_app._update_results = []
    mock_app._config.get.return_value = False
    return UpdateController(mock_app)


def _immediate_single_shot():
    """Patch ``QTimer.singleShot`` so queued UI work runs inline."""
    return patch(
        "skill_manager.controllers.update_controller.QTimer.singleShot",
        side_effect=lambda _ms, _ctx, fn: fn(),
    )


def _start_scan(controller):
    controller.scanForUpdates()
    return controller._scan_watchdog


@patch("skill_manager.controllers.update_controller.UpdateService")
def test_watchdog_clears_loading_when_worker_never_returns(mock_service_class, ctrl, mock_app):
    """A hung scan must not disable every later scan."""
    mock_app._is_loading = False
    mock_service_class.return_value.scan_for_updates.return_value = None

    watchdog = _start_scan(ctrl)

    assert mock_app._is_loading is True
    assert watchdog is not None
    assert watchdog.isActive() is True

    # Fire it exactly as the event loop would.
    watchdog.timeout.emit()

    assert mock_app._is_loading is False
    assert ctrl._scan_watchdog is None
    statuses = [call.args[0] for call in mock_app._set_status.call_args_list]
    assert any("did not respond in time" in s for s in statuses)


@patch("skill_manager.controllers.update_controller.UpdateService")
def test_scan_after_timeout_is_not_blocked(mock_service_class, ctrl, mock_app):
    """After a timeout the next scan must actually start."""
    mock_app._is_loading = False
    mock_service_class.return_value.scan_for_updates.return_value = None

    watchdog = _start_scan(ctrl)
    watchdog.timeout.emit()
    mock_app._set_status.reset_mock()

    ctrl.scanForUpdates()

    statuses = [call.args[0] for call in mock_app._set_status.call_args_list]
    assert not any("already running" in s for s in statuses)
    assert mock_app._is_loading is True


@patch("skill_manager.controllers.update_controller.UpdateService")
def test_completion_stops_watchdog_and_clears_loading(mock_service_class, ctrl, mock_app):
    mock_app._is_loading = False
    service = mock_service_class.return_value
    service.last_scan_error = None
    service.scan_for_updates.return_value = None

    _start_scan(ctrl)
    completion = service.scan_for_updates.call_args.kwargs["completion_callback"]

    with _immediate_single_shot():
        completion([{"status": "ok"}], [{"name": "A"}])

    assert mock_app._is_loading is False
    assert ctrl._scan_watchdog is None
    assert mock_app._update_results == [{"status": "ok"}]
    statuses = [call.args[0] for call in mock_app._set_status.call_args_list]
    assert any("Update scan complete" in s for s in statuses)


@patch("skill_manager.controllers.update_controller.UpdateService")
def test_late_result_after_timeout_is_discarded(mock_service_class, ctrl, mock_app):
    """A worker that finally answers must not resurrect stale state."""
    mock_app._is_loading = False
    mock_app._update_results = [{"status": "up_to_date"}]
    service = mock_service_class.return_value
    service.last_scan_error = None
    service.scan_for_updates.return_value = None

    watchdog = _start_scan(ctrl)
    completion = service.scan_for_updates.call_args.kwargs["completion_callback"]
    watchdog.timeout.emit()

    with _immediate_single_shot():
        completion([{"status": "outdated"}], [])

    assert mock_app._update_results == [{"status": "up_to_date"}]
    assert mock_app._is_loading is False


@patch("skill_manager.controllers.update_controller.UpdateService")
def test_timeout_does_not_trigger_auto_update(mock_service_class, ctrl, mock_app):
    """A partial scan must not act on stale outdated counts."""
    mock_app._is_loading = False
    mock_app._stats_outdated = 5
    mock_app._config.get.return_value = True
    mock_service_class.return_value.scan_for_updates.return_value = None

    watchdog = _start_scan(ctrl)
    with patch.object(ctrl, "updateNow") as mock_update:
        watchdog.timeout.emit()

    mock_update.assert_not_called()


@patch("skill_manager.controllers.update_controller.UpdateService")
def test_scan_failure_is_not_reported_as_complete(mock_service_class, ctrl, mock_app):
    """The service swallows its own errors; the UI must still say "failed"."""
    mock_app._is_loading = False
    service = mock_service_class.return_value
    service.last_scan_error = "discovery exploded"
    service.scan_for_updates.return_value = None

    _start_scan(ctrl)
    completion = service.scan_for_updates.call_args.kwargs["completion_callback"]

    with _immediate_single_shot():
        completion([], [])

    assert mock_app._is_loading is False
    statuses = [call.args[0] for call in mock_app._set_status.call_args_list]
    assert any("Update scan failed: discovery exploded" in s for s in statuses)
    assert not any("complete:" in s for s in statuses)


@patch("skill_manager.controllers.update_controller.UpdateService")
def test_scan_message_reports_unchecked_packages(mock_service_class, ctrl, mock_app):
    mock_app._is_loading = False
    service = mock_service_class.return_value
    service.last_scan_error = None
    service.scan_for_updates.return_value = None

    _start_scan(ctrl)
    completion = service.scan_for_updates.call_args.kwargs["completion_callback"]

    with _immediate_single_shot():
        completion(
            [], [{"name": "A", "check_status": "failed"}, {"name": "B", "check_status": "ok"}]
        )

    statuses = [call.args[0] for call in mock_app._set_status.call_args_list]
    assert any("could not check 1 package(s)" in s for s in statuses)


@patch("skill_manager.controllers.update_controller.UpdateService")
def test_start_failure_reports_and_rolls_back(mock_service_class, ctrl, mock_app):
    mock_app._is_loading = False
    mock_service_class.return_value.scan_for_updates.side_effect = RuntimeError("no thread")

    ctrl.scanForUpdates()

    assert mock_app._is_loading is False
    statuses = [call.args[0] for call in mock_app._set_status.call_args_list]
    assert any("Failed to start update scan" in s for s in statuses)


# --------------------------------------------------------------------------
# WS2 — service level
# --------------------------------------------------------------------------


@patch("skill_manager.core.update_service.check_skill_package_versions")
def test_service_passes_one_cache_for_the_whole_scan(mock_check):
    """Every package in a scan shares a single probe cache."""
    seen = []

    def fake(source, *args, **kwargs):
        seen.append(kwargs.get("remote_cache"))
        return dict(source)

    mock_check.side_effect = fake
    service = UpdateService(sources=[], projects=[], update_packages=[{"name": "A"}, {"name": "B"}])

    service.scan_for_updates_sync(lambda _s: None, lambda _r, _u: None)

    assert seen[0] is not None
    assert seen[0] is seen[1]


@patch("skill_manager.core.update_service.check_skill_package_versions")
def test_service_keeps_record_and_flags_failed_check(mock_check):
    mock_check.return_value = {"name": "A", "check_status": "failed", "check_error": "nope"}
    service = UpdateService(sources=[], projects=[], update_packages=[{"name": "A"}])

    captured = {}
    service.scan_for_updates_sync(lambda _s: None, lambda _r, u: captured.update(packages=u))

    assert captured["packages"] == [mock_check.return_value]


@patch("skill_manager.core.update_service.check_skill_package_versions")
def test_service_flags_record_when_check_raises(mock_check):
    """A raising check used to leave the record looking up to date."""
    mock_check.side_effect = RuntimeError("boom")
    service = UpdateService(sources=[], projects=[], update_packages=[{"name": "A"}])

    captured = {}
    service.scan_for_updates_sync(lambda _s: None, lambda _r, u: captured.update(packages=u))

    assert captured["packages"][0]["check_status"] == "failed"
    assert "boom" in captured["packages"][0]["check_error"]


@patch("skill_manager.core.update_service.discover_package_skills")
def test_service_records_scan_error(mock_discover):
    mock_discover.side_effect = RuntimeError("kaboom")
    service = UpdateService(sources=[], projects=[], update_packages=[])
    statuses = []

    service.scan_for_updates_sync(statuses.append, lambda _r, _u: None)

    assert service.last_scan_error == "kaboom"
    assert any("Scan failed: kaboom" in s for s in statuses)


def test_service_resets_scan_error_between_runs():
    service = UpdateService(sources=[], projects=[], update_packages=[])
    service.last_scan_error = "stale"

    service.scan_for_updates_sync(lambda _s: None, lambda _r, _u: None)

    assert service.last_scan_error is None


def test_update_service_normalises_packages():
    service = UpdateService(sources=[], projects=[], update_packages=[{"name": "  A  "}])
    assert isinstance(service.update_packages[0], dict)
    assert service.last_scan_error is None


def test_controller_fixture_has_watchdog_attribute():
    """Sanity: the watchdog lives on the instance, not in a global."""
    ctrl = UpdateController(MagicMock())
    assert ctrl._scan_watchdog is None


# --------------------------------------------------------------------------
# WS3 — data safety
# --------------------------------------------------------------------------


def _resolve_with_empty_inventory(ctrl):
    """Run storage resolution without touching the real package inventory."""
    with patch("skill_manager.core.persistence.load_package_skill_inventory", return_value={}):
        ctrl._resolvePackageStorageState()


def test_storage_resolution_keeps_unparseable_record(ctrl, mock_app):
    """A malformed record must not vanish and repoint its neighbours.

    The old code dropped records that failed validation, and because the
    write-back is positional, every later package inherited the previous
    package's storage path.
    """
    mock_app._update_packages = [
        {"name": "First", "package_id": "first"},
        {"name": "Bad", "package_id": "bad", "managed_folders": "not-a-list"},
        {"name": "Third", "package_id": "third"},
    ]

    _resolve_with_empty_inventory(ctrl)

    assert [p["name"] for p in mock_app._update_packages] == ["First", "Bad", "Third"]
    assert [p["package_id"] for p in mock_app._update_packages] == ["first", "bad", "third"]


def test_storage_resolution_preserves_update_error(ctrl, mock_app):
    """``update_error`` is shown by the UI, so it must survive a round trip.

    ``UpdatePackageRecord`` used to omit the field while ``extra="ignore"``
    silently discarded it on every validation pass.
    """
    mock_app._update_packages = [
        {"name": "A", "package_id": "a", "update_error": "boom", "current_version": "1.0"}
    ]

    _resolve_with_empty_inventory(ctrl)

    assert mock_app._update_packages[0]["update_error"] == "boom"


def test_update_error_is_a_declared_schema_field():
    record = UpdatePackageRecord.model_validate({"name": "A", "update_error": "boom"})
    assert record.update_error == "boom"


@patch("skill_manager.core.skill_packages.delete_package_storage")
def test_removal_aborts_when_storage_deletion_fails(mock_delete, ctrl, mock_app):
    """A failed cleanup must not silently orphan files on disk."""
    mock_app._update_packages = [{"name": "Bad", "package_id": "bad"}]
    mock_delete.return_value = {"errors": ["permission denied"], "deleted_skill_paths": []}

    with (
        patch("skill_manager.core.persistence.load_package_skill_inventory", return_value={}),
        patch("skill_manager.core.persistence.load_project_skill_ownership", return_value={}),
    ):
        ctrl.removeUpdatePackage(0)

    # Record kept so the removal can be retried.
    assert mock_app._update_packages == [{"name": "Bad", "package_id": "bad"}]
    statuses = [call.args[0] for call in mock_app._set_status.call_args_list]
    assert any("Could not remove Bad" in s for s in statuses)
    assert not any("Removed update package" in s for s in statuses)


@patch("skill_manager.core.skill_packages.delete_package_storage")
def test_removal_proceeds_when_storage_is_clean(mock_delete, ctrl, mock_app):
    mock_app._update_packages = [{"name": "Good", "package_id": "good"}]
    mock_delete.return_value = {"errors": [], "deleted_skill_paths": []}

    with (
        patch("skill_manager.core.persistence.load_package_skill_inventory", return_value={}),
        patch("skill_manager.core.persistence.load_project_skill_ownership", return_value={}),
        patch.object(ctrl, "_resolvePackageStorageState"),
    ):
        ctrl.removeUpdatePackage(0)

    assert mock_app._update_packages == []
    statuses = [call.args[0] for call in mock_app._set_status.call_args_list]
    assert any("Removed update package: Good" in s for s in statuses)


def test_config_save_is_atomic(tmp_path):
    """A failed config write must leave the previous file intact."""
    from skill_manager.core import config as config_module

    target = tmp_path / "config.json"
    with patch.object(config_module, "resolve_data_file", return_value=target):
        manager = config_module.ConfigManager()

    manager.data = {"ok": True}
    manager.save()
    assert orjson.loads(target.read_bytes()) == {"ok": True}
    assert list(tmp_path.glob("*.tmp")) == []

    before = target.read_bytes()
    manager.data = {"unserialisable": object()}
    manager.save()

    assert target.read_bytes() == before
    assert list(tmp_path.glob("*.tmp")) == []


def test_add_skill_package_reports_pending_install(ctrl, mock_app):
    """Add must not claim success while the install is still pending."""
    mock_app._update_packages = []
    data = {
        "name": "Pkg",
        "source_type": "git",
        "package_id": "pkg",
        "repository_url": "https://github.com/o/r.git",
    }
    unchecked = {
        "check_status": "failed",
        "check_error": "unreachable",
        "latest_version": "latest",
    }

    with (
        patch(
            "skill_manager.core.skill_packages.check_skill_package_versions",
            return_value=unchecked,
        ) as mock_check,
        patch.object(ctrl, "_resolvePackageStorageState"),
        patch("skill_manager.controllers.update_controller.QTimer.singleShot"),
    ):
        payload = json.loads(ctrl.addSkillPackage(data))

    assert payload["ok"] is True
    assert payload["installing"] is True
    assert payload["warning"] == "unreachable"

    record = mock_app._update_packages[0]
    assert record["last_updated"] == "Installing…"
    assert record["check_status"] == "failed"

    # Both detection phases must share one probe cache.
    assert len(mock_check.call_args_list) == 2
    caches = {id(call.kwargs.get("remote_cache")) for call in mock_check.call_args_list}
    assert len(caches) == 1
    assert None not in caches


def test_add_skill_package_without_warning_when_probe_succeeds(ctrl, mock_app):
    mock_app._update_packages = []
    data = {"name": "Pkg", "source_type": "git", "package_id": "pkg"}

    with (
        patch(
            "skill_manager.core.skill_packages.check_skill_package_versions",
            return_value={
                "check_status": "ok",
                "check_error": "",
                "latest_version": "1.0.0",
            },
        ),
        patch.object(ctrl, "_resolvePackageStorageState"),
        patch("skill_manager.controllers.update_controller.QTimer.singleShot"),
    ):
        payload = json.loads(ctrl.addSkillPackage(data))

    assert payload["ok"] is True
    assert payload["warning"] == ""


# --------------------------------------------------------------------------
# WS4 — a failed check is visible and recoverable
# --------------------------------------------------------------------------


def test_count_unchecked_packages():
    assert count_unchecked_packages(None) == 0
    assert count_unchecked_packages([]) == 0
    assert (
        count_unchecked_packages(
            [
                {"check_status": "ok"},
                {"check_status": "failed"},
                {"check_status": "failed"},
                {},
            ]
        )
        == 2
    )


def test_recalculate_stats_reports_unchecked(ctrl, mock_app):
    """ "0 updates" must be distinguishable from "0 packages checked"."""
    mock_app._update_results = []
    mock_app._update_packages = [
        {"package_id": "a", "check_status": "failed"},
        {"package_id": "b", "check_status": "ok"},
        {
            "package_id": "c",
            "check_status": "failed",
            "current_version": "1.0",
            "latest_version": "2.0",
        },
    ]

    ctrl.recalculateStats()

    assert mock_app._stats_unchecked == 2
    assert mock_app._stats_outdated == 1


def test_retry_package_check_clears_failed_state(ctrl, mock_app):
    """A retry puts the package back to a known-good check state."""
    mock_app._update_packages = [
        {"name": "Pkg", "package_id": "pkg", "check_status": "failed", "check_error": "offline"}
    ]

    with (
        patch(
            "skill_manager.core.skill_packages.check_skill_package_versions",
            return_value={
                "name": "Pkg",
                "package_id": "pkg",
                "check_status": "ok",
                "check_error": "",
                "latest_version": "2.0.0",
            },
        ),
        _immediate_single_shot(),
    ):
        ctrl.retryPackageCheck("pkg")

    record = mock_app._update_packages[0]
    assert record["check_status"] == "ok"
    assert record["check_error"] == ""
    statuses = [call.args[0] for call in mock_app._set_status.call_args_list]
    assert any("Checking Pkg" in s for s in statuses)
    assert "Checked Pkg" in statuses
    assert mock_app._stats_unchecked == 0


def test_retry_package_check_reports_failure(ctrl, mock_app):
    """A raising probe is a reported failure, not a silent no-op."""
    mock_app._update_packages = [{"name": "Pkg", "package_id": "pkg"}]

    with (
        patch(
            "skill_manager.core.skill_packages.check_skill_package_versions",
            side_effect=RuntimeError("boom"),
        ),
        patch("skill_manager.controllers.update_controller.capture_exception"),
        _immediate_single_shot(),
    ):
        ctrl.retryPackageCheck("pkg")

    record = mock_app._update_packages[0]
    assert record["check_status"] == "failed"
    assert "boom" in record["check_error"]
    statuses = [call.args[0] for call in mock_app._set_status.call_args_list]
    assert any(s.startswith("Could not check Pkg") for s in statuses)


def test_retry_package_check_ignores_unknown_package(ctrl, mock_app):
    mock_app._update_packages = [{"name": "Pkg", "package_id": "pkg"}]

    with patch("skill_manager.core.skill_packages.check_skill_package_versions") as mock_check:
        ctrl.retryPackageCheck("does-not-exist")

    mock_check.assert_not_called()


def test_retry_package_check_discards_result_when_package_removed(ctrl, mock_app):
    """A row removed while the probe ran must not be resurrected."""
    mock_app._update_packages = [{"name": "Pkg", "package_id": "pkg"}]

    def probe_then_remove(*_args, **_kwargs):
        mock_app._update_packages.clear()
        return {"name": "Pkg", "package_id": "pkg", "check_status": "ok"}

    with (
        patch(
            "skill_manager.core.skill_packages.check_skill_package_versions",
            side_effect=probe_then_remove,
        ),
        _immediate_single_shot(),
    ):
        ctrl.retryPackageCheck("pkg")

    assert mock_app._update_packages == []
    statuses = [call.args[0] for call in mock_app._set_status.call_args_list]
    assert "Checked Pkg" not in statuses


# --------------------------------------------------------------------------
# WS5 — bounded work and coalesced rescans
# --------------------------------------------------------------------------


def test_discovery_refresh_is_coalesced(ctrl, mock_app):
    """Rapid package changes must not stack full filesystem scans."""
    mock_app.loadInitialData = MagicMock()
    queued = []

    def collect(_ms, _ctx, fn):
        queued.append(fn)

    with patch(
        "skill_manager.controllers.update_controller.QTimer.singleShot", side_effect=collect
    ):
        ctrl._schedule_discovery_refresh()
        ctrl._schedule_discovery_refresh()
        ctrl._schedule_discovery_refresh()

    assert len(queued) == 1
    mock_app.loadInitialData.assert_not_called()

    queued[0]()
    mock_app.loadInitialData.assert_called_once()

    # The guard releases once the refresh has run, so the next change counts.
    with patch(
        "skill_manager.controllers.update_controller.QTimer.singleShot", side_effect=collect
    ):
        ctrl._schedule_discovery_refresh()
    assert len(queued) == 2


def test_edit_shares_one_probe_cache_across_phases(ctrl, mock_app):
    """Both edit phases must reuse one probe instead of listing the remote twice."""
    mock_app._update_packages = [{"name": "Pkg", "package_id": "pkg", "source_type": "git"}]

    with (
        patch(
            "skill_manager.core.skill_packages.check_skill_package_versions",
            side_effect=lambda source, **kwargs: {**source, "latest_version": "2.0.0"},
        ) as mock_check,
        patch.object(ctrl, "_resolvePackageStorageState"),
    ):
        ctrl.updateUpdatePackage(0, {"name": "Pkg", "package_id": "pkg", "source_type": "git"})

    assert len(mock_check.call_args_list) == 2
    caches = {id(call.kwargs.get("remote_cache")) for call in mock_check.call_args_list}
    assert len(caches) == 1
    assert None not in caches
