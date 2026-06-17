from unittest.mock import MagicMock, patch

import pytest

from skill_manager.controllers.update_controller import UpdateController
from skill_manager.core.schemas import UpdatePackageRecord


@pytest.fixture
def mock_app():
    app = MagicMock()
    app._update_packages = []
    app._sources = []
    app._projects = []
    app._project_aliases = {}
    app._syncing_projects = []
    app._config = MagicMock()
    app._library_model = MagicMock()
    app._quick_copy_model = MagicMock()
    app.task_runner = MagicMock()
    return app


@pytest.fixture
def controller(mock_app):
    return UpdateController(mock_app)


class TestUpdateControllerSDET:
    def test_add_update_package_basic_validation(self, controller, mock_app):
        # Happy path
        controller.addUpdatePackage("test-package")
        assert len(mock_app._update_packages) == 1
        record = UpdatePackageRecord.model_validate(mock_app._update_packages[0])
        assert record.name == "test-package"
        assert record.source_type == "npx"

        # Empty name should early return
        mock_app._update_packages = []
        controller.addUpdatePackage("")
        assert len(mock_app._update_packages) == 0

    def test_add_skill_package_strict_schema(self, controller, mock_app):
        data = {
            "name": "My Git Package",
            "source_type": "git",
            "package_id": "my-git",
            "extra_field": "should-be-ignored",
        }

        with patch(
            "skill_manager.core.skill_packages.check_skill_package_versions",
            side_effect=lambda x: x,
        ):
            controller.addSkillPackage(data)

        assert len(mock_app._update_packages) == 1
        record = mock_app._update_packages[0]
        assert record["name"] == "My Git Package"
        assert "extra_field" not in record
        assert record["is_updating"] is False
        assert record["last_updated"] == "Never"

    def test_add_skill_package_invalid_data(self, controller, mock_app):
        # source_type should be git, npx, local, or custom.
        # But we don't have strict Enum yet, let's see what happens with missing required fields if any.
        # Currently UpdatePackageRecord has all optional defaults.
        # Let's test a case where validation might fail if we had constraints.
        pass

    def test_update_update_package_persistence(self, controller, mock_app):
        mock_app._update_packages = [{"name": "Old", "package_id": "p1", "source_type": "npx"}]

        new_data = {"name": "New", "package_id": "p1", "source_type": "git"}

        with patch(
            "skill_manager.core.skill_packages.check_skill_package_versions",
            side_effect=lambda x: x,
        ):
            controller.updateUpdatePackage(0, new_data)

        assert mock_app._update_packages[0]["name"] == "New"
        assert mock_app._update_packages[0]["source_type"] == "git"

    def test_resolve_package_storage_state_recovery(self, controller, mock_app):
        # Simulate corrupted config data
        mock_app._update_packages = [
            {"name": "Valid", "package_id": "v1"},
            {"name": None},  # This will trigger coercion/validation
        ]

        with patch(
            "skill_manager.core.skill_packages.resolve_package_storage", side_effect=lambda p, i: p
        ):
            controller._resolvePackageStorageState()

        assert len(mock_app._update_packages) == 2
        assert mock_app._update_packages[1]["name"] == ""  # Coerced to empty string

    @patch("skill_manager.controllers.update_controller.UpdateService")
    def test_scan_for_updates_silent_auto_trigger(self, mock_service_class, controller, mock_app):
        mock_service = mock_service_class.return_value
        mock_app._config.get.side_effect = lambda k, default=None: {
            "skill_package_auto_update": True,
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
            patch.object(controller, "updateNow") as mock_update_now,
        ):
            controller.scanForUpdates()
            # recalculateStats should have set stats_outdated = 1
            assert mock_app._stats_outdated == 1
            mock_update_now.assert_called_once()

    def test_remove_update_package(self, controller, mock_app):
        mock_app._update_packages = [{"name": "To Remove"}]
        controller.removeUpdatePackage(0)
        assert len(mock_app._update_packages) == 0
        mock_app.updatePackagesChanged.emit.assert_called()
