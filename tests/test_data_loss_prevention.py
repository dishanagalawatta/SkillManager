"""Tests for data-loss prevention: test isolation, discovery safety net,
legacy config fallback, and source path validation.

ADR-0011 related: protects against catastrophic cache wipe when
source directories are missing or test data leaks into production.
"""

import os
import tempfile
import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from skill_manager.controllers.discovery_controller import DiscoveryController
from skill_manager.core.config import ConfigManager
from skill_manager.core.diagnostics import (
    CATEGORY_CACHE_PRESERVED,
    CATEGORY_CONFIG_MIGRATION,
    CATEGORY_DISCOVERY_EMPTY_RESULT,
    CATEGORY_SOURCE_MISSING,
    CATEGORY_WINDOW_STATE,
)
from skill_manager.core.schemas import CacheState, SkillRecord


@pytest.fixture
def temp_data_dir():
    path = Path(tempfile.gettempdir()) / f"sm-dlp-test-{uuid.uuid4().hex}"
    path.mkdir(parents=True)
    yield path
    import shutil

    shutil.rmtree(path, ignore_errors=True)


class TestDiscoverySafetyNet:
    """Verify that discovery does not wipe cached skills when sources are missing."""

    def _make_controller(self, app):
        return DiscoveryController(app)

    def test_safety_net_triggers_when_final_returns_zero(self, temp_data_dir):
        """Final discovery returning 0 skills with non-empty cache should preserve skills."""
        app = MagicMock()
        app._sources = []
        app._update_packages = []
        app._projects = []
        app._archive_paths = []
        app._starred_paths = []
        app._project_aliases = {}
        app._categories = []
        app._client_format = "Gemini"
        app._current_project_label = ""
        app._library_model = MagicMock()
        app._quick_copy_model = MagicMock()
        app.ops = MagicMock()

        ctrl = self._make_controller(app)
        ctrl._previous_skills = {
            "/p/s1": SkillRecord(name="S1", local_path="/p/s1"),
            "/p/s2": SkillRecord(name="S2", local_path="/p/s2"),
        }

        state = CacheState(
            skills=[],
            categories=[],
            status="Found 0 skills (0 projects)",
        )
        ctrl._finalize_loading(state, is_final=True)

        # Skills should NOT be removed
        app._library_model.removeSkillsByPath.assert_not_called()
        app._quick_copy_model.removeSkillsByPath.assert_not_called()
        app._library_model.setSkills.assert_not_called()
        assert app._is_loading is False

    def test_safety_net_does_not_trigger_for_non_final(self, temp_data_dir):
        """Non-final discovery returning 0 skills should not trigger safety net."""
        app = MagicMock()
        app._sources = []
        app._update_packages = []
        app._projects = []
        app._archive_paths = []
        app._starred_paths = []
        app._project_aliases = {}
        app._categories = []
        app._client_format = "Gemini"
        app._current_project_label = ""
        app._library_model = MagicMock()
        app._quick_copy_model = MagicMock()
        app.ops = MagicMock()

        ctrl = self._make_controller(app)
        ctrl._previous_skills = {
            "/p/s1": SkillRecord(name="S1", local_path="/p/s1"),
        }

        state = CacheState(skills=[], status="Found 0 skills")
        ctrl._finalize_loading(state, is_final=False)

        # Non-final with 0 skills: incremental path removes old skills
        app._library_model.removeSkillsByPath.assert_called_once()

    def test_safety_net_does_not_trigger_when_new_skills_exist(self, temp_data_dir):
        """When new skills are discovered, safety net should not trigger even if some are removed."""
        app = MagicMock()
        app._sources = []
        app._update_packages = []
        app._projects = []
        app._archive_paths = []
        app._starred_paths = []
        app._project_aliases = {}
        app._categories = []
        app._client_format = "Gemini"
        app._current_project_label = ""
        app._library_model = MagicMock()
        app._quick_copy_model = MagicMock()
        app.ops = MagicMock()

        ctrl = self._make_controller(app)
        ctrl._previous_skills = {
            "/p/s1": SkillRecord(name="S1", local_path="/p/s1"),
            "/p/s2": SkillRecord(name="S2", local_path="/p/s2"),
        }

        # One skill kept, one removed
        state = CacheState(
            skills=[SkillRecord(name="S1", local_path="/p/s1")],
            categories=[],
            status="Found 1 skills",
        )
        ctrl._finalize_loading(state, is_final=True)

        # Safety net should NOT trigger — incremental update removes only s2
        app._library_model.removeSkillsByPath.assert_called_once_with(["/p/s2"])


class TestLegacyConfigFallback:
    """Verify legacy config targets→projects fallback."""

    def test_fallback_merges_targets_when_no_projects(self, temp_data_dir):
        """App-data config without projects + legacy with targets → merge."""
        data_dir = temp_data_dir / "data"
        data_dir.mkdir()

        # App-data config has no projects
        (data_dir / "config.json").write_text('{"sources": [], "shortcuts": {}}', encoding="utf-8")

        # Create a fake CWD with legacy data/config.json
        fake_cwd = temp_data_dir / "cwd"
        fake_cwd.mkdir()
        legacy_data = fake_cwd / "data"
        legacy_data.mkdir()
        (legacy_data / "config.json").write_text(
            '{"targets": ["proj-a", "proj-b"]}', encoding="utf-8"
        )

        with (
            patch.dict(os.environ, {"SKILL_MANAGER_DATA_DIR": str(data_dir)}, clear=False),
            patch("skill_manager.core.config.Path.cwd", return_value=fake_cwd),
        ):
            mgr = ConfigManager()

        assert mgr.get("projects") == ["proj-a", "proj-b"]

    def test_fallback_does_not_overwrite_existing_projects(self, temp_data_dir):
        """If app-data already has projects, legacy targets should not overwrite."""
        data_dir = temp_data_dir / "data"
        data_dir.mkdir()

        (data_dir / "config.json").write_text(
            '{"projects": ["existing"], "shortcuts": {}}', encoding="utf-8"
        )

        fake_cwd = temp_data_dir / "cwd"
        fake_cwd.mkdir()
        legacy_data = fake_cwd / "data"
        legacy_data.mkdir()
        (legacy_data / "config.json").write_text('{"targets": ["legacy"]}', encoding="utf-8")

        with (
            patch.dict(os.environ, {"SKILL_MANAGER_DATA_DIR": str(data_dir)}, clear=False),
            patch("skill_manager.core.config.Path.cwd", return_value=fake_cwd),
        ):
            mgr = ConfigManager()

        assert mgr.get("projects") == ["existing"]


class TestDiagnosticCategories:
    """Verify new diagnostic categories are defined and importable."""

    def test_new_categories_exist(self):
        assert CATEGORY_DISCOVERY_EMPTY_RESULT == "discovery_empty_result"
        assert CATEGORY_CACHE_PRESERVED == "cache_preserved"
        assert CATEGORY_SOURCE_MISSING == "source_missing"
        assert CATEGORY_CONFIG_MIGRATION == "config_migration"

    def test_window_state_category_exists(self):
        assert CATEGORY_WINDOW_STATE == "window_state"


class TestSourcePathValidation:
    """Verify source path validation in DiscoveryService."""

    def test_missing_sources_logged(self, temp_data_dir):
        """DiscoveryService should log warnings for missing source paths."""
        from skill_manager.core.diagnostics import get_diagnostic_logger
        from skill_manager.core.discovery import DiscoveryService

        diag = get_diagnostic_logger()
        diag.clear_logs()
        diag.set_enabled(True)

        svc = DiscoveryService(
            sources=["/nonexistent/path/abc123"],
            projects=["/nonexistent/path/def456"],
        )

        svc.discover_all(use_cache=False)

        events = diag.get_recent_events(50)
        source_missing_events = [e for e in events if e.get("category") == CATEGORY_SOURCE_MISSING]
        assert len(source_missing_events) >= 2  # both source and project

        diag.set_enabled(False)


class TestRecoveryScriptWindowState:
    """Verify recovery script fixes corrupted window state (off-screen coordinates)."""

    def _run_recovery_with_ui_state(self, ui_state, legacy_targets=None):
        """Helper: run recovery with given UI state and optional legacy targets."""
        import json
        import shutil
        import tempfile
        from importlib.util import module_from_spec, spec_from_file_location
        from pathlib import Path

        tmp = Path(tempfile.mkdtemp())
        data_dir = tmp / "appdata"
        data_dir.mkdir()
        legacy_dir = tmp / "legacy" / "data"
        legacy_dir.mkdir(parents=True)

        # Write app-data config with corrupted UI state
        app_config = {"sources": [], "projects": [], "ui_state": ui_state}
        (data_dir / "config.json").write_text(json.dumps(app_config), encoding="utf-8")

        # Write legacy config with targets
        targets = legacy_targets or [str(tmp / "real_project")]
        (tmp / "real_project").mkdir(exist_ok=True)
        legacy_config = {"targets": targets}
        (legacy_dir / "config.json").write_text(json.dumps(legacy_config), encoding="utf-8")

        # Import recover_settings module directly. The dynamic import +
        # module-level attribute patching below is a deliberate test
        # isolation trick that pyright can't infer (``spec_from_file_location``
        # returns ``None`` only for an invalid spec; the script_path above
        # is hard-coded and known-valid, and ``ModuleType`` permits arbitrary
        # attribute assignment at runtime even though the stub type forbids it).
        script_path = Path(__file__).resolve().parent.parent / "scripts" / "recover_settings.py"
        spec = spec_from_file_location("recover_settings", script_path)  # type: ignore[assignment]
        mod = module_from_spec(spec)  # type: ignore[arg-type]
        spec.loader.exec_module(mod)  # type: ignore[union-attr]

        orig_app = mod.APP_DATA_CONFIG
        orig_legacy = mod.LEGACY_CONFIG
        mod.APP_DATA_CONFIG = data_dir / "config.json"  # type: ignore[attr-defined]
        mod.LEGACY_CONFIG = legacy_dir / "config.json"  # type: ignore[attr-defined]

        try:
            mod.recover()
            result = json.loads((data_dir / "config.json").read_text(encoding="utf-8"))
            return result.get("ui_state", {})
        finally:
            mod.APP_DATA_CONFIG = orig_app  # type: ignore[attr-defined]
            mod.LEGACY_CONFIG = orig_legacy  # type: ignore[attr-defined]
            shutil.rmtree(tmp, ignore_errors=True)

    def test_fixes_offscreen_window_x(self):
        """Off-screen window_x should be reset to 100."""
        result = self._run_recovery_with_ui_state(
            {
                "window_x": -32000,
                "window_y": 200,
                "window_width": 1200,
                "window_height": 800,
            }
        )
        assert result["window_x"] == 100
        assert result["window_y"] == 200  # preserved

    def test_fixes_offscreen_window_y(self):
        """Off-screen window_y should be reset to 100."""
        result = self._run_recovery_with_ui_state(
            {
                "window_x": 200,
                "window_y": -32000,
                "window_width": 1200,
                "window_height": 800,
            }
        )
        assert result["window_x"] == 200  # preserved
        assert result["window_y"] == 100

    def test_fixes_zero_opacity(self):
        """Zero window_opacity should be reset to 1.0."""
        result = self._run_recovery_with_ui_state(
            {
                "window_x": 200,
                "window_y": 200,
                "window_opacity": 0.0,
            }
        )
        assert result["window_opacity"] == 1.0

    def test_fixes_tiny_dimensions(self):
        """Window dimensions < 400 should be reset to defaults."""
        result = self._run_recovery_with_ui_state(
            {
                "window_x": 200,
                "window_y": 200,
                "window_width": 100,
                "window_height": 50,
            }
        )
        assert result["window_width"] == 1200
        assert result["window_height"] == 800

    def test_preserves_valid_ui_state(self):
        """Valid UI state should not be modified."""
        original = {
            "window_x": 500,
            "window_y": 300,
            "window_width": 1400,
            "window_height": 900,
            "window_opacity": 1.0,
        }
        result = self._run_recovery_with_ui_state(original)
        assert result == original
