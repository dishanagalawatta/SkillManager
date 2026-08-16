"""Unit and integration tests for path repair, storage normalization, and model incubation coordination fixes."""

from unittest.mock import MagicMock

import pytest

from skill_manager.core.copier import repair_malformed_path
from skill_manager.core.models.entities import PreparedModelState, Skill
from skill_manager.core.models.qt_model import SkillModel
from skill_manager.core.skill_packages.config import normalize_skill_package_config
from skill_manager.core.skill_packages.storage import resolve_package_storage


class TestPathRepair:
    """Tests for repair_malformed_path."""

    def test_repair_missing_leading_slash(self):
        """Path starting with home/ without leading slash is repaired to /home/..."""
        raw = "home/dikka/.agent/skills"
        repaired = repair_malformed_path(raw)
        assert repaired.startswith("/home/")
        assert repaired == "/home/dikka/.agent/skills"

    def test_repair_users_missing_leading_slash(self):
        """Path starting with Users/ without leading slash is repaired to /Users/..."""
        raw = "Users/dikka/.agent/skills"
        repaired = repair_malformed_path(raw)
        assert repaired.startswith("/Users/")
        assert repaired == "/Users/dikka/.agent/skills"

    def test_repair_duplicated_home_root(self):
        """Path with duplicated /home/user/home/user/... root is stripped to the inner canonical root."""
        raw = "/home/dikka/home/dikka/.agent/skills/marketing-skills-9a1d6353"
        repaired = repair_malformed_path(raw)
        assert repaired == "/home/dikka/.agent/skills/marketing-skills-9a1d6353"

    def test_repair_empty_path(self):
        """Empty or whitespace path returns empty string."""
        assert repair_malformed_path("") == ""
        assert repair_malformed_path("   ") == ""

    def test_repair_clean_path_unchanged(self):
        """Clean absolute path is returned unchanged."""
        clean = "/home/dikka/Documents/01-Projects/27-SkillManager"
        assert repair_malformed_path(clean) == clean


class TestPackageStorageResolution:
    """Tests for package storage resolution and config normalization."""

    def test_resolve_package_storage_with_malformed_configured_path(self):
        """Package with relative 'home/...' configured path resolves to /home/... without duplication."""
        packages = [
            {
                "name": "Marketing Skills",
                "package_id": "pkg_6afa9a1d6353",
                "configured_package_path": "home/dikka/.agent/skills",
                "package_path": "/home/dikka/home/dikka/.agent/skills/marketing-skills-9a1d6353",
            }
        ]
        resolved = resolve_package_storage(packages)
        assert len(resolved) == 1
        pkg = resolved[0]
        assert pkg["configured_package_path"] == "/home/dikka/.agent/skills"
        assert not pkg["package_path"].startswith("/home/dikka/home/dikka")
        assert pkg["package_path"] == "/home/dikka/.agent/skills/marketing-skills-9a1d6353"

    def test_normalize_skill_package_config_repairs_paths(self):
        """normalize_skill_package_config sanitizes malformed configured and resolved paths."""
        data = {
            "name": "Test Package",
            "source_type": "git",
            "repository_url": "https://github.com/example/test",
            "configured_package_path": "home/user/.agent/skills",
            "package_path": "/home/user/home/user/.agent/skills/test-pkg",
            "clone_path": "/home/user/home/user/.local/share/SkillManager/package_clones/test-pkg",
        }
        normalized = normalize_skill_package_config(data)
        assert normalized["configured_package_path"] == "/home/user/.agent/skills"
        assert normalized["package_path"] == "/home/user/.agent/skills/test-pkg"
        assert (
            normalized["clone_path"]
            == "/home/user/.local/share/SkillManager/package_clones/test-pkg"
        )


@pytest.mark.usefixtures("setup_qml_style")
class TestIncubationAndCommitFlow:
    """Tests for model incubation and DiscoveryController commit flow."""

    def test_replace_prepared_state_applies_without_incubation_lock(self, qtbot):
        """replacePreparedState applies state smoothly without entering stalled incubation."""
        model = SkillModel()
        skill = Skill(
            name="Skill 1", local_path="/path/1", is_package=True, main_category="General"
        )
        state = PreparedModelState(
            all_skills=[skill],
            search_engine=None,
            all_filtered_skills=[skill],
            visible_rows=[skill],
            categories=["General"],
            status="Done",
            generation=1,
            is_final=True,
        )

        # Apply state
        model.replacePreparedState(state)

        # Model should have the skill
        assert model._all_skills == [skill]
        assert model._filtered_skills == [skill]
        assert not model.incubating
        assert not model._pending_signals

    def test_discovery_controller_commit_does_not_deadlock_incubation(self):
        """_commit_prepared_state updates models without artificially setting incubating flag."""
        from skill_manager.controllers.discovery_controller import DiscoveryController

        mock_app = MagicMock()
        mock_lib_model = SkillModel()
        mock_qc_model = SkillModel()
        mock_app._library_model = mock_lib_model
        mock_app._quick_copy_model = mock_qc_model
        mock_app._client_format = "Plain Text"
        mock_app._current_project_label = "Project A"
        mock_app._categories = []
        mock_app._previous_skills = {}
        mock_app._config = {}

        controller = DiscoveryController(mock_app)
        controller._refresh_generation = 1

        skill = Skill(
            name="Test Skill", local_path="/path/test", is_package=True, main_category="General"
        )
        state = PreparedModelState(
            all_skills=[skill],
            search_engine=None,
            all_filtered_skills=[skill],
            visible_rows=[skill],
            categories=["General"],
            status="Complete",
            generation=1,
            is_final=True,
        )

        controller._commit_prepared_state({"library": state, "quick_copy": state})

        # Verify models are immediately populated and not stalled in incubation
        assert mock_lib_model._all_skills == [skill]
        assert mock_qc_model._all_skills == [skill]
        assert not mock_lib_model.incubating
        assert not mock_qc_model.incubating
        assert not mock_lib_model._pending_signals
        assert not mock_qc_model._pending_signals
