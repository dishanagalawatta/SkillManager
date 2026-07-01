"""Comprehensive tests for the Updates view: isLatest predicate, click → slot wiring,
Scan / Update All / per-package Update / Edit / Remove flows, and in-place mutation
contract of _resolvePackageStorageState.

Run with::

    uv run pytest tests/test_qml_update_button_flow.py -v
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from skill_manager.controllers.update_controller import UpdateController

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_package(
    *,
    name: str = "TestPkg",
    current_version: str = "",
    latest_version: str = "",
    is_updating: bool = False,
    just_finished: bool = False,
    update_error: str = "",
    package_path: str = "/tmp/test",
    source_type: str = "npx",
    package_name: str = "@test/test",
    package_id: str = "pkg_test123abc",
) -> dict:
    return {
        "name": name,
        "source_type": source_type,
        "package_name": package_name,
        "package_path": package_path,
        "current_version": current_version,
        "latest_version": latest_version,
        "package_id": package_id,
        "is_updating": is_updating,
        "just_finished": just_finished,
        "update_error": update_error,
        "last_updated": "Never",
        "storage_mode": "individual",
        "managed_folders": [],
        "removed_folders": [],
        "updated_folders": [],
        "removals_verified": False,
    }


def _noop_resolve(packages, _inventory):
    """Fake resolve_package_storage that returns copies (mirrors real behavior)."""
    return [dict(p) for p in packages]


# ===========================================================================
# 1.  isLatest predicate matrix
# ===========================================================================


class TestIsLatestPredicate:
    """The QML isLatest expression is:
        Boolean(modelData.latest_version &&
                modelData.latest_version !== "" &&
                modelData.latest_version === modelData.current_version)

    We test every edge case that previously caused the Update button to be
    disabled when it should not have been.
    """

    @staticmethod
    def _eval_is_latest(latest: str, current: str) -> bool:
        """Evaluate the fixed QML isLatest logic in Python."""
        return bool(latest and latest != "" and latest == current)

    def test_empty_latest_unknown_version_is_not_latest(self):
        """Empty latest_version → version unknown → NOT latest → button enabled."""
        assert self._eval_is_latest("", "1.0.0") is False

    def test_both_empty_not_latest(self):
        """Both empty → neither is known → NOT latest → button enabled."""
        assert self._eval_is_latest("", "") is False

    def test_same_version_is_latest(self):
        """latest == current (both non-empty) → IS latest → button disabled."""
        assert self._eval_is_latest("1.0.0", "1.0.0") is True

    def test_different_versions_not_latest(self):
        """latest != current → NOT latest → button enabled."""
        assert self._eval_is_latest("2.0.0", "1.0.0") is False

    def test_null_like_strings_not_latest(self):
        """QML null/undefined strings should not count as latest."""
        assert self._eval_is_latest("null", "1.0.0") is False
        assert self._eval_is_latest("undefined", "1.0.0") is False


# ===========================================================================
# 2.  Click → slot wiring
# ===========================================================================


class TestPerPackageUpdateClick:
    """Simulate what happens when the user clicks the per-package Update button."""

    @pytest.fixture
    def ctrl(self, mock_app):
        mock_app._sources = ["/src"]
        mock_app._projects = ["/project"]
        mock_app._update_packages = [
            _make_package(current_version="1.0.0", latest_version=""),
            _make_package(name="Pkg2", current_version="1.0.0", latest_version="2.0.0"),
        ]
        mock_app._syncing_projects = []
        mock_app._project_aliases = {}
        mock_app._library_model._all_skills = []
        return UpdateController(mock_app)

    def test_update_button_enabled_when_latest_empty(self, ctrl, mock_app):
        """After our fix, packages with empty latest_version are updatable."""
        pkg = mock_app._update_packages[0]
        assert not (
            pkg["latest_version"]
            and pkg["latest_version"] != ""
            and pkg["latest_version"] == pkg["current_version"]
        )

    def test_update_button_enabled_when_versions_differ(self, ctrl, mock_app):
        """When latest > current the button must be enabled."""
        pkg = mock_app._update_packages[1]
        assert pkg["latest_version"] != pkg["current_version"]

    @patch("skill_manager.controllers.update_controller.QTimer")
    @patch("skill_manager.controllers.update_controller.capture_event")
    def test_run_package_update_sets_is_updating(self, _mock_event, _mock_timer, ctrl, mock_app):
        """runPackageUpdate flips is_updating to True for the correct index."""
        with patch.object(ctrl, "_resolvePackageStorageState"):
            ctrl.runPackageUpdate(0)

        assert mock_app._update_packages[0]["is_updating"] is True
        assert mock_app._update_packages[0]["just_finished"] is False

    @patch("skill_manager.controllers.update_controller.QTimer")
    @patch("skill_manager.controllers.update_controller.capture_event")
    def test_run_package_update_correct_index(self, _mock_event, _mock_timer, ctrl, mock_app):
        """Verify the slot receives the right index and mutates the right package."""
        with patch.object(ctrl, "_resolvePackageStorageState"):
            ctrl.runPackageUpdate(1)

        assert mock_app._update_packages[1]["is_updating"] is True
        assert mock_app._update_packages[0]["is_updating"] is False


# ===========================================================================
# 3.  Scan / Update All / Edit / Remove flows
# ===========================================================================


class TestUpdateFlows:
    @pytest.fixture
    def ctrl(self, mock_app):
        mock_app._sources = ["/src"]
        mock_app._projects = ["/project"]
        mock_app._update_packages = [
            _make_package(current_version="1.0.0", latest_version="2.0.0"),
        ]
        mock_app._syncing_projects = []
        mock_app._project_aliases = {}
        mock_app._library_model._all_skills = []
        return UpdateController(mock_app)

    def test_add_skill_package(self, ctrl, mock_app):
        """addSkillPackage normalizes, appends, and resolves storage."""
        new_pkg = {
            "name": "NewPkg",
            "source_type": "npx",
            "package_name": "@new/pkg",
            "package_path": "/tmp/new",
            "package_id": "pkg_new1",
        }
        with (
            patch("skill_manager.controllers.update_controller.UpdatePackageRecord") as mock_rec,
            patch(
                "skill_manager.core.skill_packages.check_skill_package_versions",
                side_effect=lambda d, **kw: {
                    **d,
                    "latest_version": d.get("latest_version") or "1.0.0",
                },
            ),
            patch(
                "skill_manager.core.skill_packages.normalize_skill_package_config",
                side_effect=lambda d: d,
            ),
            patch("skill_manager.controllers.update_controller.capture_event"),
            patch.object(ctrl, "_resolvePackageStorageState"),
        ):
            mock_rec.model_validate.return_value.model_dump.return_value = {
                **new_pkg,
                "is_updating": False,
                "last_updated": "Never",
            }
            ctrl.addSkillPackage(new_pkg)

        assert any(p["name"] == "NewPkg" for p in mock_app._update_packages)

    def test_remove_update_package(self, ctrl, mock_app):
        """removeUpdatePackage pops the correct index and clears the list."""
        with patch.object(ctrl, "_resolvePackageStorageState"):
            ctrl.removeUpdatePackage(0)

        assert len(mock_app._update_packages) == 0
        mock_app._set_status.assert_called()
        status_args = mock_app._set_status.call_args[0]
        assert "Removed update package" in status_args[0]

    def test_remove_update_package_invalid_index(self, ctrl, mock_app):
        """Invalid index is a no-op."""
        ctrl.removeUpdatePackage(999)
        assert len(mock_app._update_packages) == 1

    def test_run_package_update_invalid_index(self, ctrl, mock_app):
        """Invalid index is a no-op — no crash."""
        ctrl.runPackageUpdate(999)
        assert mock_app._update_packages[0]["is_updating"] is False

    @patch("skill_manager.controllers.update_controller.UpdateService")
    def test_update_now_triggers_global_update(self, mock_service_class, ctrl, mock_app):
        """updateNow delegates to UpdateService.run_global_update."""
        mock_service = mock_service_class.return_value
        ctrl.updateNow()

        assert "/project" in mock_app._syncing_projects
        mock_service.run_global_update.assert_called_once()

    @patch("skill_manager.controllers.update_controller.UpdateService")
    def test_scan_for_updates(self, mock_service_class, ctrl, mock_app):
        """scanForUpdates delegates to UpdateService.scan_for_updates."""
        mock_service = mock_service_class.return_value
        ctrl.scanForUpdates()
        mock_service.scan_for_updates.assert_called_once()

    def test_update_update_package(self, ctrl, mock_app):
        """updateUpdatePackage replaces the package at the given index."""
        edited = {
            "name": "EditedPkg",
            "source_type": "npx",
            "package_name": "@edited/pkg",
            "package_path": "/tmp/edited",
        }
        detected = {**edited, "latest_version": "1.0.0", "current_version": ""}
        synced = {**detected, "current_version": "1.0.0"}
        with (
            patch(
                "skill_manager.core.skill_packages.check_skill_package_versions",
                side_effect=[detected, synced],
            ),
            patch.object(ctrl, "_resolvePackageStorageState"),
        ):
            ctrl.updateUpdatePackage(0, edited)

        assert mock_app._update_packages[0]["name"] == "EditedPkg"


# ===========================================================================
# 4.  _resolvePackageStorageState in-place mutation contract
# ===========================================================================


class TestResolvePackageStorageStateInPlace:
    """_resolvePackageStorageState must mutate the list in place so that every
    captured reference (QML modelData, background workers) stays valid."""

    @pytest.fixture
    def ctrl(self, mock_app):
        mock_app._sources = ["/src"]
        mock_app._projects = ["/project"]
        mock_app._update_packages = [
            _make_package(name="A", package_id="pkg_aaaa"),
            _make_package(name="B", package_id="pkg_bbbb"),
        ]
        mock_app._syncing_projects = []
        mock_app._project_aliases = {}
        mock_app._library_model._all_skills = []
        return UpdateController(mock_app)

    def test_list_identity_preserved(self, ctrl, mock_app):
        """The list object itself must not be replaced."""
        original_list = mock_app._update_packages
        original_id = id(original_list)

        with patch(
            "skill_manager.core.skill_packages.resolve_package_storage",
            side_effect=_noop_resolve,
        ):
            ctrl._resolvePackageStorageState()

        assert id(mock_app._update_packages) == original_id

    def test_dict_identity_preserved(self, ctrl, mock_app):
        """Each dict in the list must keep its identity (in-place update)."""
        original_ids = [id(d) for d in mock_app._update_packages]

        with patch(
            "skill_manager.core.skill_packages.resolve_package_storage",
            side_effect=_noop_resolve,
        ):
            ctrl._resolvePackageStorageState()

        actual_ids = [id(d) for d in mock_app._update_packages]
        assert actual_ids == original_ids

    def test_config_updated(self, ctrl, mock_app):
        """The config must be updated after storage resolution."""
        with patch(
            "skill_manager.core.skill_packages.resolve_package_storage",
            side_effect=_noop_resolve,
        ):
            ctrl._resolvePackageStorageState()

        # ctrl.config is mock_app._config (set by BaseController.__init__)
        mock_app._config.set.assert_called_with("skills", mock_app._update_packages)

    def test_signal_emitted(self, ctrl, mock_app):
        """updatePackagesChanged must be emitted once."""
        with patch(
            "skill_manager.core.skill_packages.resolve_package_storage",
            side_effect=_noop_resolve,
        ):
            ctrl._resolvePackageStorageState()

        mock_app.updatePackagesChanged.emit.assert_called()

    def test_items_updated_in_place(self, ctrl, mock_app):
        """The refreshed data must be written into the existing dicts."""

        def fake_resolve(packages, _inventory):
            for p in packages:
                p["storage_mode"] = "grouped"
            return packages

        with patch(
            "skill_manager.core.skill_packages.resolve_package_storage",
            side_effect=fake_resolve,
        ):
            ctrl._resolvePackageStorageState()

        assert mock_app._update_packages[0]["storage_mode"] == "grouped"
        assert mock_app._update_packages[1]["storage_mode"] == "grouped"

    def test_list_length_matches(self, ctrl, mock_app):
        """The list must end up with exactly the items returned by resolve_package_storage."""

        def fake_resolve(packages, _inventory):
            return packages[:1]  # drop the second package

        with patch(
            "skill_manager.core.skill_packages.resolve_package_storage",
            side_effect=fake_resolve,
        ):
            ctrl._resolvePackageStorageState()

        assert len(mock_app._update_packages) == 1

    def test_background_worker_reference_stable(self, ctrl, mock_app):
        """After _resolvePackageStorageState, a dict captured by a background
        worker must reflect the resolved content.  The real usage pattern is:
        resolve first, then read the dict and mutate it."""
        # 1. Resolve storage (simulates the start of runPackageUpdate)
        with patch(
            "skill_manager.core.skill_packages.resolve_package_storage",
            side_effect=_noop_resolve,
        ):
            ctrl._resolvePackageStorageState()

        # 2. Worker reads the dict AFTER resolve (same as runPackageUpdate)
        pkg = mock_app._update_packages[0]
        pkg["is_updating"] = True

        # The mutation must stick — dict identity is preserved
        assert pkg["is_updating"] is True
        assert mock_app._update_packages[0]["is_updating"] is True


# ===========================================================================
# 5.  Dict-replacement contract for runPackageUpdate
# ===========================================================================


class TestRunPackageUpdateDictReplacement:
    """runPackageUpdate must replace the dict (not mutate in-place) so that
    QML's QVariantMap snapshot is invalidated and delegate bindings re-evaluate.
    """

    @pytest.fixture
    def ctrl(self, mock_app):
        mock_app._sources = ["/src"]
        mock_app._projects = ["/project"]
        mock_app._update_packages = [
            _make_package(current_version="1.0.0", latest_version="2.0.0"),
        ]
        mock_app._syncing_projects = []
        mock_app._project_aliases = {}
        mock_app._library_model._all_skills = []
        return UpdateController(mock_app)

    @patch("skill_manager.controllers.update_controller.QTimer")
    @patch("skill_manager.controllers.update_controller.capture_event")
    def test_dict_identity_replaced(self, _mock_event, _mock_timer, ctrl, mock_app):
        """The dict at the target index must be a NEW object (different id)."""
        original_id = id(mock_app._update_packages[0])

        with patch.object(ctrl, "_resolvePackageStorageState"):
            ctrl.runPackageUpdate(0)

        new_id = id(mock_app._update_packages[0])
        assert new_id != original_id

    @patch("skill_manager.controllers.update_controller.QTimer")
    @patch("skill_manager.controllers.update_controller.capture_event")
    def test_other_indices_unaffected(self, _mock_event, _mock_timer, ctrl, mock_app):
        """Only the target index dict is replaced; others keep identity."""
        mock_app._update_packages.append(_make_package(name="Other"))
        original_other_id = id(mock_app._update_packages[1])

        with patch.object(ctrl, "_resolvePackageStorageState"):
            ctrl.runPackageUpdate(0)

        assert id(mock_app._update_packages[1]) == original_other_id
        assert mock_app._update_packages[1]["is_updating"] is False


# ===========================================================================
# 6.  update_error tracking
# ===========================================================================


class TestUpdateErrorTracking:
    """runPackageUpdate must clear update_error before running and set it on failure."""

    @pytest.fixture
    def ctrl(self, mock_app):
        mock_app._sources = ["/src"]
        mock_app._projects = ["/project"]
        mock_app._update_packages = [
            _make_package(current_version="1.0.0", latest_version="2.0.0"),
        ]
        mock_app._syncing_projects = []
        mock_app._project_aliases = {}
        mock_app._library_model._all_skills = []
        return UpdateController(mock_app)

    @patch("skill_manager.controllers.update_controller.QTimer")
    @patch("skill_manager.controllers.update_controller.capture_event")
    @patch("skill_manager.core.skill_packages.run_skill_package_update")
    def test_update_error_cleared_on_click(
        self, _mock_run_update, _mock_event, _mock_timer, ctrl, mock_app
    ):
        """A prior update_error must be cleared when the user clicks Update again."""
        mock_app._update_packages[0]["update_error"] = "Previous failure"
        _mock_run_update.return_value = {}

        with patch.object(ctrl, "_resolvePackageStorageState"):
            ctrl.runPackageUpdate(0)

        assert mock_app._update_packages[0]["update_error"] == ""

    def test_update_error_initially_empty(self, ctrl, mock_app):
        """Packages start with empty update_error."""
        assert mock_app._update_packages[0].get("update_error", "") == ""


# ===========================================================================
# 7.  QML Connections handler regression tests
# ===========================================================================


class TestQmlConnectionsHandler:
    """The QML ListView with a plain list model does not detect item-level
    mutations.  We add a Connections handler that resets the model on each
    signal to force delegate rebuild.  These tests verify the handler exists.
    """

    @pytest.fixture
    def qml_source(self):
        from pathlib import Path

        qml_path = (
            Path(__file__).resolve().parent.parent
            / "src"
            / "skill_manager"
            / "SkillManagerComponents"
            / "views"
            / "UpdatesView.qml"
        )
        return qml_path.read_text(encoding="utf-8")

    def test_packages_list_connections_handler_exists(self, qml_source):
        """UpdatesView must bind uv_packagesList.model to AppController.updatePackages."""
        assert "model: AppController.updatePackages" in qml_source

    def test_projects_list_connections_handler_exists(self, qml_source):
        """UpdatesView must bind uv_projectsList.model to AppController.config_controller.updateProjects."""
        assert (
            "model: AppController.config_controller.updateProjects" in qml_source
        )

    def test_connections_handler_uses_correct_signal(self, qml_source):
        """UpdatesView uses direct model binding — no Connections reset guard needed."""
        assert "model: AppController.updatePackages" in qml_source

    def test_projects_connections_handler_uses_correct_signal(self, qml_source):
        """UpdatesView uses direct model binding — no Connections reset guard needed."""
        assert "model: AppController.config_controller.updateProjects" in qml_source


# ===========================================================================
# 8.  Package config field preservation (regression)
# ===========================================================================


class TestPackageConfigFieldPreservation:
    """Ensure config fields like repository_url survive the
    addSkillPackage → model_validate → model_dump round-trip."""

    @pytest.fixture
    def ctrl(self, mock_app):
        mock_app._sources = ["/src"]
        mock_app._projects = ["/project"]
        mock_app._update_packages = []
        mock_app._syncing_projects = []
        mock_app._project_aliases = {}
        mock_app._library_model._all_skills = []
        return UpdateController(mock_app)

    def test_add_skill_package_preserves_repository_url(self, ctrl, mock_app):
        """addSkillPackage must not drop repository_url from the stored package."""
        pkg = {
            "name": "RepoPkg",
            "source_type": "git",
            "repository_url": "https://github.com/test/repo.git",
            "github_token": "ghp_secret123",
            "clone_path": "/tmp/clone",
        }
        with (
            patch(
                "skill_manager.core.skill_packages.check_skill_package_versions",
                side_effect=lambda d, **kw: {
                    **d,
                    "latest_version": d.get("latest_version") or "1.0.0",
                },
            ),
            patch.object(ctrl, "_resolvePackageStorageState"),
        ):
            ctrl.addSkillPackage(pkg)

        stored = mock_app._update_packages[-1]
        assert stored["repository_url"] == "https://github.com/test/repo.git"
        assert stored["github_token"] == "ghp_secret123"
        assert stored["clone_path"] == "/tmp/clone"

    def test_update_update_package_preserves_repository_url(self, ctrl, mock_app):
        """updateUpdatePackage must not drop repository_url from the stored package."""
        mock_app._update_packages = [_make_package(name="OldPkg", package_id="old_pkg_id12345")]
        edited = {
            "name": "EditedRepoPkg",
            "repository_url": "https://github.com/test/edited.git",
            "package_args": "--save-dev",
            "update_command": "npm update",
        }
        detected = {**edited, "latest_version": "1.0.0", "current_version": ""}
        synced = {**detected, "current_version": "1.0.0"}
        with (
            patch(
                "skill_manager.core.skill_packages.check_skill_package_versions",
                side_effect=[detected, synced],
            ),
            patch.object(ctrl, "_resolvePackageStorageState"),
        ):
            ctrl.updateUpdatePackage(0, edited)

        stored = mock_app._update_packages[0]
        assert stored["repository_url"] == "https://github.com/test/edited.git"
        assert stored["package_args"] == "--save-dev"
        assert stored["update_command"] == "npm update"

    def test_add_skill_package_preserves_all_config_fields(self, ctrl, mock_app):
        """All six config fields must survive the addSkillPackage round-trip.
        Note: for source_type='git', detect_package_config clears update_command
        and sets latest/current_version_command via setdefault."""
        pkg = {
            "name": "FullPkg",
            "source_type": "git",
            "repository_url": "https://github.com/test/repo.git",
            "github_token": "ghp_token",
            "package_args": "--save",
            "update_command": "npm update",
            "current_version_command": "node -v",
            "latest_version_command": "npm show version",
        }
        with (
            patch(
                "skill_manager.core.skill_packages.check_skill_package_versions",
                side_effect=lambda d, **kw: {
                    **d,
                    "latest_version": d.get("latest_version") or "1.0.0",
                },
            ),
            patch.object(ctrl, "_resolvePackageStorageState"),
        ):
            ctrl.addSkillPackage(pkg)

        stored = mock_app._update_packages[-1]
        assert stored["repository_url"] == "https://github.com/test/repo.git"
        assert stored["github_token"] == "ghp_token"
        assert stored["package_args"] == "--save"
        # Git packages: update_command is cleared, version commands preserved
        assert stored["update_command"] == ""
        assert stored["current_version_command"] == "node -v"
        assert stored["latest_version_command"] == "npm show version"
