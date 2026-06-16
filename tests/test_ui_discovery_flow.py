from unittest.mock import patch

import pytest

from skill_manager.core.schemas import SkillRecord


@pytest.mark.usefixtures("setup_qml_style")
class TestUIDiscoveryFlow:
    def test_load_initial_data_flow(self, qml_engine, app_controller, qtbot):
        """Verify the full flow from calling loadInitialData to model update."""

        # Reset models and filters for a clean test
        app_controller.libraryModel.setSkills([])
        app_controller.quickCopyModel.setSkills([])
        app_controller.discovery._previous_skills = {}

        # Mock the DiscoveryService.discover_all to return a fixed state
        with patch("skill_manager.controllers.discovery_controller.DiscoveryService") as mock_service_class:
            mock_service = mock_service_class.return_value

            # Setup discovery result
            # IMPORTANT: is_package must be True because models filter for packages by default
            mock_skills = [
                {"name": "Skill Alpha", "local_path": "/path/alpha", "category": "General", "is_package": True},
                {"name": "Skill Beta", "local_path": "/path/beta", "category": "Tests", "is_package": True}
            ]
            mock_service.discover_all.return_value = {
                "skills": mock_skills,
                "projects": [],
                "categories": ["General", "Tests"],
                "project_labels": [],
                "status": "Scan Complete"
            }

            # 1. Trigger discovery
            app_controller.discovery.loadInitialData()

            # 2. Wait for completion (isLoading -> False)
            # Since task_runner is synchronous in tests, it might already be False.
            # We wait just to ensure UI signals processed.
            qtbot.waitUntil(lambda: app_controller.isLoading is False, timeout=5000)

            # 3. Verify Model synchronization
            # The app_controller.skillModel should now have the skills
            assert app_controller.libraryModel.rowCount() == 2

            # 4. Verify UI state
            assert app_controller.statusMessage == "Scan Complete"
            assert "General" in app_controller.categories
            assert "Tests" in app_controller.categories

    def test_incremental_discovery_ui_update(self, qml_engine, app_controller, qtbot):
        """Verify that discovery updates existing models incrementally."""

        # 1. Inject initial state into models
        initial_skills = [
            {"name": "Old Skill", "local_path": "/old", "category": "Misc", "is_package": True}
        ]
        app_controller.libraryModel.setSkills(initial_skills)
        app_controller.discovery._previous_skills = {
            "/old": SkillRecord(name="Old Skill", local_path="/old", category="Misc", is_package=True)
        }

        # 2. Mock discovery with one added skill
        with patch("skill_manager.controllers.discovery_controller.DiscoveryService") as mock_service_class:
            mock_service = mock_service_class.return_value
            mock_service.discover_all.return_value = {
                "skills": [
                    {"name": "Old Skill", "local_path": "/old", "category": "Misc", "is_package": True},
                    {"name": "New Skill", "local_path": "/new", "category": "Misc", "is_package": True}
                ],
                "projects": [],
                "categories": ["Misc"],
                "project_labels": [],
                "status": "Update Done"
            }

            # 3. Trigger discovery
            app_controller.discovery.loadInitialData()

            # 4. Wait for completion
            qtbot.waitUntil(lambda: app_controller.isLoading is False, timeout=5000)

            # 5. Verify models updated
            assert app_controller.libraryModel.rowCount() == 2
            assert app_controller.statusMessage == "Update Done"

            # Verify specific skill names
            names = [app_controller.libraryModel.data(app_controller.libraryModel.index(i, 0), app_controller.libraryModel.NameRole) for i in range(2)]
            assert "New Skill" in names
            assert "Old Skill" in names
