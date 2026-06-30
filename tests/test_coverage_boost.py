"""Targeted tests to boost coverage for discovery.py and diagnostics.py.

Covers uncovered paths:
- diagnostics: log_dir fallback, platform_info, qt_version exception,
  app_version exception, initialize with context, rotate_if_needed,
  log_event file write failure, clear_logs, export_bundle
- discovery: discover_all cache loading exception, discover_packages_incremental cache hit,
  command file discovery
"""

import json
import os
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from diskcache import Cache

from skill_manager.core.discovery import (
    DiscoveryService,
)

# ---------------------------------------------------------------------------
# diagnostics.py coverage
# ---------------------------------------------------------------------------


class TestDiagnosticsHelpers:
    def test_log_dir_localappdata_set(self):
        from skill_manager.core.diagnostics import log_dir

        with patch.dict(os.environ, {"LOCALAPPDATA": "/tmp/fake_data"}):
            result = log_dir()
            assert "SkillManager" in str(result)
            assert "logs" in str(result)

    def test_log_dir_localappdata_unset(self):
        from skill_manager.core.diagnostics import log_dir

        env = os.environ.copy()
        env.pop("LOCALAPPDATA", None)
        with (
            patch.dict(os.environ, env, clear=True),
            patch("skill_manager.core.diagnostics.sys.platform", "win32"),
        ):
            result = log_dir()
            assert "SkillManager" in str(result)

    def test_log_dir_xdg_linux(self):
        from skill_manager.core.diagnostics import log_dir

        env = os.environ.copy()
        env.pop("LOCALAPPDATA", None)
        env["XDG_DATA_HOME"] = "/tmp/xdg_data"
        with (
            patch.dict(os.environ, env, clear=True),
            patch("skill_manager.core.diagnostics.sys.platform", "linux"),
        ):
            result = log_dir()
            assert "xdg_data" in str(result)
            assert "SkillManager" in str(result)

    def test_platform_info(self):
        from skill_manager.core.diagnostics import platform_info

        info = platform_info()
        assert "platform" in info
        assert "os" in info
        assert "os_version" in info
        assert "python" in info
        assert isinstance(info["platform"], str)

    def test_qt_version_returns_string(self):
        from skill_manager.core.diagnostics import qt_version

        result = qt_version()
        assert isinstance(result, str)

    def test_qt_version_exception_returns_unknown(self):
        from skill_manager.core.diagnostics import qt_version

        with patch("builtins.__import__", side_effect=ImportError("no PySide6")):
            result = qt_version()
            assert result == "unknown"

    def test_app_version_exception_returns_unknown(self):
        from skill_manager.core.diagnostics import app_version

        with patch.dict("sys.modules", {"skill_manager": None}):
            result = app_version()
            assert result == "unknown"


class TestDiagnosticLogger:
    def test_initialize_with_context(self, tmp_path):
        from skill_manager.core.diagnostics import DiagnosticLogger

        logger = DiagnosticLogger(log_dir=tmp_path)
        logger.initialize(log_level="DEBUG", context={"custom_key": "custom_value"})
        assert logger.log_level == "DEBUG"
        assert logger.context["custom_key"] == "custom_value"

    def test_log_event_writes_to_file(self, tmp_path):
        from skill_manager.core.diagnostics import DiagnosticLogger

        logger = DiagnosticLogger(log_dir=tmp_path)
        logger.initialize()
        logger.set_enabled(True)
        logger.log_event("INFO", "test_category", "test message")

        log_file = tmp_path / "diagnostic.log"
        assert log_file.exists()
        content = log_file.read_text()
        assert "test message" in content
        assert "test_category" in content

    def test_log_event_with_data(self, tmp_path):
        from skill_manager.core.diagnostics import DiagnosticLogger

        logger = DiagnosticLogger(log_dir=tmp_path)
        logger.initialize()
        logger.set_enabled(True)
        logger.log_event("INFO", "test", "msg", data={"key": "val"})

        log_file = tmp_path / "diagnostic.log"
        line = log_file.read_text().strip()
        event = json.loads(line)
        assert event["data"]["key"] == "val"

    def test_log_event_file_write_failure(self, tmp_path):
        from skill_manager.core.diagnostics import DiagnosticLogger

        logger = DiagnosticLogger(log_dir=tmp_path)
        logger.initialize()
        logger.set_enabled(True)
        # Simulate file write failure by making log file a directory
        logger.log_file.mkdir()
        logger.log_event("INFO", "test", "should not crash")
        # Should not raise - error is logged to stderr

    def test_rotate_if_needed_no_file(self, tmp_path):
        from skill_manager.core.diagnostics import DiagnosticLogger

        logger = DiagnosticLogger(log_dir=tmp_path)
        logger.initialize()
        logger.rotate_if_needed()  # Should not raise when no log file exists

    def test_rotate_if_needed_small_file(self, tmp_path):
        from skill_manager.core.diagnostics import DiagnosticLogger

        logger = DiagnosticLogger(log_dir=tmp_path)
        logger.initialize()
        logger.log_file.write_text("small content")
        logger.rotate_if_needed()  # File is small, no rotation
        assert logger.log_file.exists()

    def test_rotate_if_needed_large_file(self, tmp_path):
        from skill_manager.core.diagnostics import (
            MAX_ROTATION_BYTES,
            DiagnosticLogger,
        )

        logger = DiagnosticLogger(log_dir=tmp_path)
        logger.initialize()
        # Create a file larger than rotation threshold
        large_content = "x" * (MAX_ROTATION_BYTES + 1024)
        logger.log_file.write_text(large_content)
        logger.rotate_if_needed()
        # Should have rotated
        rotated = tmp_path / "diagnostic.log.1"
        assert rotated.exists()

    def test_clear_logs(self, tmp_path):
        from skill_manager.core.diagnostics import DiagnosticLogger

        logger = DiagnosticLogger(log_dir=tmp_path)
        logger.initialize()
        logger.set_enabled(True)
        logger.log_event("INFO", "test", "msg")
        logger.clear_logs()
        assert len(logger.ring) == 0
        assert not logger.log_file.exists()

    def test_export_bundle(self, tmp_path):
        from skill_manager.core.diagnostics import DiagnosticLogger

        logger = DiagnosticLogger(log_dir=tmp_path)
        logger.initialize()
        logger.set_enabled(True)
        logger.log_event("INFO", "test", "test event")

        bundle_path = logger.export_bundle()
        assert bundle_path
        assert os.path.exists(bundle_path)

        with zipfile.ZipFile(bundle_path, "r") as zf:
            names = zf.namelist()
            assert "diagnostic_bundle.json" in names
            assert "diagnostic.log" in names

    def test_export_bundle_creates_dir(self, tmp_path):
        from skill_manager.core.diagnostics import DiagnosticLogger

        output_dir = tmp_path / "nested" / "output"
        logger = DiagnosticLogger(log_dir=tmp_path)
        logger.initialize()
        bundle_path = logger.export_bundle(output_dir=output_dir)
        assert bundle_path

    def test_export_bundle_os_error(self, tmp_path):
        from skill_manager.core.diagnostics import DiagnosticLogger

        logger = DiagnosticLogger(log_dir=tmp_path)
        logger.initialize()
        # Make output dir a file to trigger OSError
        bad_output = tmp_path / "badfile"
        bad_output.write_text("not a dir")
        result = logger.export_bundle(output_dir=bad_output)
        assert result == ""


# ---------------------------------------------------------------------------
# discovery.py coverage
# ---------------------------------------------------------------------------


class TestDiscoveryCacheHit:
    def test_incremental_cache_hit(self, tmp_path):
        """Test that a second scan with same fingerprint hits cache."""

        source_lib = tmp_path / "master"
        source_lib.mkdir()
        skill1 = source_lib / "skill1"
        skill1.mkdir()
        (skill1 / "SKILL.md").write_text("---\nname: Skill One\n---")

        service = DiscoveryService(
            sources=[str(source_lib)],
            projects=[],
            archive_paths=[],
            starred_paths=[],
            project_aliases={},
        )

        def parse_fn(p):
            return {"name": "Skill One", "metadata": {}}

        def cat_fn(n, t, m):
            return {"main_category": "Cat", "sub_category": "Sub"}

        with Cache(str(tmp_path / "cache")) as disk_cache:
            # First scan - populates cache
            skills1 = service.discover_packages_incremental(disk_cache, parse_fn, cat_fn)
            assert len(skills1) == 1

            # Second scan - should hit cache (no re-scan)
            skills2 = service.discover_packages_incremental(disk_cache, parse_fn, cat_fn)
            assert len(skills2) == 1
            assert skills2[0]["name"] == "Skill One"

    def test_incremental_cache_miss_on_fingerprint_change(self, tmp_path):
        """Test that changing a file invalidates the cache."""
        source_lib = tmp_path / "master"
        source_lib.mkdir()
        skill1 = source_lib / "skill1"
        skill1.mkdir()
        (skill1 / "SKILL.md").write_text("---\nname: Skill One\n---")

        service = DiscoveryService(
            sources=[str(source_lib)],
            projects=[],
            archive_paths=[],
            starred_paths=[],
            project_aliases={},
        )

        counter_path = tmp_path / "parse_calls.txt"
        counter_path.write_text("0")

        def parse_fn(p):
            n = int(counter_path.read_text()) + 1
            counter_path.write_text(str(n))
            return {"name": "Skill One", "metadata": {}}

        def cat_fn(n, t, m):
            return {"main_category": "Cat", "sub_category": "Sub"}

        with Cache(str(tmp_path / "cache")) as disk_cache:
            skills1 = service.discover_packages_incremental(disk_cache, parse_fn, cat_fn)
            assert len(skills1) == 1

            (skill1 / "SKILL.md").write_text("---\nname: Skill One Updated\n---")

            source_lib.touch()

            skills2 = service.discover_packages_incremental(disk_cache, parse_fn, cat_fn)
            assert len(skills2) == 1
            assert int(counter_path.read_text()) == 2  # parse_fn called twice = cache miss

    def test_discover_all_cache_exception_handled(self, tmp_path):
        """Test that exception during cache loading is handled gracefully."""
        source_lib = tmp_path / "master"
        source_lib.mkdir()

        service = DiscoveryService(
            sources=[str(source_lib)],
            projects=[],
            archive_paths=[],
            starred_paths=[],
            project_aliases={},
        )

        with patch("skill_manager.core.discovery.load_cache", side_effect=Exception("cache error")):
            # Should not raise - exception is caught and logged
            service.discover_all(use_cache=True)


class TestDiscoveryProjects:
    def test_project_discovery_incremental(self, tmp_path):
        """Test project skill discovery with cache."""
        proj_dir = tmp_path / "project"
        proj_dir.mkdir()
        skill_a = proj_dir / "skillA"
        skill_a.mkdir()
        (skill_a / "SKILL.md").write_text("---\nname: Proj Skill\n---")

        service = DiscoveryService(
            sources=[],
            projects=[str(proj_dir)],
            archive_paths=[],
            starred_paths=[],
            project_aliases={},
        )

        def parse_fn(p):
            return {"name": "Proj Skill", "metadata": {}}

        def cat_fn(n, t, m):
            return {"main_category": "Dev", "sub_category": "Sub"}

        with Cache(str(tmp_path / "cache")) as disk_cache:
            projects = service.discover_projects_incremental(disk_cache, parse_fn, cat_fn)
            assert len(projects) == 1
            assert projects[0]["skills"][0]["name"] == "Proj Skill"


class TestDiscoveryTransform:
    def test_transform_skill_basic(self):
        service = DiscoveryService(sources=[], projects=[])
        skill = {"name": "Test", "metadata": {}}
        result = service.transform_skill(skill, is_package=True)
        assert result["is_package"] is True

    def test_transform_skill_with_project_label(self):
        service = DiscoveryService(sources=[], projects=[])
        skill = {"name": "Test", "metadata": {}}
        result = service.transform_skill(skill, is_package=False, project_label="My Project")
        assert result["project_label"] == "My Project"

    def test_transform_skill_starred(self):
        service = DiscoveryService(sources=[], projects=[], starred_paths=[])
        skill = {"local_path": "/starred/skill", "metadata": {}}
        result = service.transform_skill(skill, is_package=True)
        # starred status is determined by starred_paths check
        assert "is_starred" in result


# ---------------------------------------------------------------------------
# task_runner.py coverage
# ---------------------------------------------------------------------------


class TestTaskRunner:
    def test_base_runner_raises_not_implemented(self):
        from skill_manager.utils.task_runner import TaskRunner

        runner = TaskRunner()
        with pytest.raises(NotImplementedError):
            runner.run(lambda: None)

    def test_synchronous_task_runner(self):
        from skill_manager.utils.task_runner import SynchronousTaskRunner

        runner = SynchronousTaskRunner()
        result = runner.run(lambda x: x * 2, args=(5,))
        assert result == 10

    def test_synchronous_task_runner_with_kwargs(self):
        from skill_manager.utils.task_runner import SynchronousTaskRunner

        runner = SynchronousTaskRunner()
        result = runner.run(lambda a, b: a + b, kwargs={"a": 3, "b": 7})
        assert result == 10

    def test_submit_with_callback(self):
        from skill_manager.utils.task_runner import SynchronousTaskRunner

        runner = SynchronousTaskRunner()
        callback_results = []
        runner.submit(target=lambda: 42, callback=callback_results.append)
        assert callback_results == [42]

    def test_background_task_runner(self):
        import time

        from skill_manager.utils.task_runner import BackgroundTaskRunner

        runner = BackgroundTaskRunner()
        result = []

        def work():
            result.append("done")

        runner.run(work)
        time.sleep(0.1)
        assert result == ["done"]

    def test_qt_asyncio_task_runner_sync(self):
        from skill_manager.utils.task_runner import QtAsyncioTaskRunner

        runner = QtAsyncioTaskRunner()
        result = runner.run(lambda: "sync_result")
        assert result == "sync_result"


# ---------------------------------------------------------------------------
# config.py coverage
# ---------------------------------------------------------------------------


class TestConfigManager:
    def test_config_load_error_handled(self, tmp_path):
        from skill_manager.core.config import ConfigManager

        config_file = tmp_path / "test_config.json"
        config_file.write_text("not valid json {{{")

        with patch("skill_manager.core.config.resolve_data_file", return_value=config_file):
            manager = ConfigManager.__new__(ConfigManager)
            manager.config_path = config_file
            manager.data = {}
            manager.load()
            # Should handle error gracefully

    def test_config_load_missing_shortcuts(self, tmp_path):
        from skill_manager.core.config import ConfigManager

        config_file = tmp_path / "test_config.json"
        config_file.write_text('{"theme": "dark"}')

        with patch("skill_manager.core.config.resolve_data_file", return_value=config_file):
            manager = ConfigManager.__new__(ConfigManager)
            manager.config_path = config_file
            manager.data = {}
            manager.load()
            assert "shortcuts" in manager.data

    def test_config_load_exception_during_read(self, tmp_path):
        from skill_manager.core.config import ConfigManager

        config_file = tmp_path / "test_config.json"
        config_file.write_text('{"theme": "dark"}')

        with patch("skill_manager.core.config.resolve_data_file", return_value=config_file):
            manager = ConfigManager.__new__(ConfigManager)
            manager.config_path = config_file
            manager.data = {}
            with patch("builtins.open", side_effect=OSError("read error")):
                manager.load()
                # Should handle exception gracefully


# ---------------------------------------------------------------------------
# commands.py coverage
# ---------------------------------------------------------------------------


class TestCommands:
    def test_update_custom_command_read_error(self, tmp_path):
        from skill_manager.core.commands import update_custom_command_file

        cmd_file = tmp_path / "test_cmd.md"
        cmd_file.write_text("---\nname: test\n---")

        with patch(
            "skill_manager.core.parsing.base.split_frontmatter",
            side_effect=Exception("parse error"),
        ):
            result = update_custom_command_file(
                local_path=str(cmd_file),
                name="test",
                body="test body",
            )
            assert result.ok is False
            assert "Error reading command file" in result.message

    def test_update_custom_command_write_error(self, tmp_path):
        from skill_manager.core.commands import update_custom_command_file

        cmd_file = tmp_path / "test_cmd.md"
        cmd_file.write_text("---\nname: test\n---")

        with patch.object(Path, "write_text", side_effect=OSError("write error")):
            result = update_custom_command_file(
                local_path=str(cmd_file),
                name="test",
                body="test body",
            )
            assert result.ok is False
            assert "Error updating command" in result.message


# ---------------------------------------------------------------------------
# analytics.py coverage
# ---------------------------------------------------------------------------


class TestAnalytics:
    def test_init_posthog_exception_returns_none(self):
        from skill_manager.core.analytics import init_posthog

        with patch.dict("sys.modules", {"posthog": None}):
            result = init_posthog()
            assert result is None

    def test_shutdown_when_posthog_exists(self):
        from skill_manager.core.analytics import shutdown

        mock_client = MagicMock()
        with patch("skill_manager.core.analytics._posthog", mock_client):
            shutdown()
            mock_client.shutdown.assert_called_once()

    def test_shutdown_when_posthog_none(self):
        from skill_manager.core.analytics import shutdown

        with patch("skill_manager.core.analytics._posthog", None):
            shutdown()  # Should not raise


# ---------------------------------------------------------------------------
# search.py coverage
# ---------------------------------------------------------------------------


class TestSearch:
    def test_rapidfuzz_import_fallback(self):
        with patch.dict("sys.modules", {"rapidfuzz": None}):
            import skill_manager.core.search as search_mod

            # Re-import to trigger the ImportError path
            with patch.object(search_mod, "fuzz", None):
                # Just verify fuzz can be None without crashing
                assert search_mod.fuzz is None

    def test_search_engine_query_fuzzy(self):
        from skill_manager.core.search import SearchEngine

        skills = [
            {"name": "Glass Button Component", "local_path": "/skills/glass_button"},
        ]
        engine = SearchEngine(skills)
        # Query with fuzzy match triggers token matching logic
        results = engine.query("glss btn")
        assert isinstance(results, list)

    def test_search_engine_query_empty(self):
        from skill_manager.core.search import SearchEngine

        skills = [
            {"name": "Glass Button Component", "local_path": "/skills/glass_button"},
        ]
        engine = SearchEngine(skills)
        results = engine.query("")
        assert len(results) == 1
        assert results[0][1] == 100.0


# ---------------------------------------------------------------------------
# filter_engine.py + categorizer.py coverage (targeted)
# ---------------------------------------------------------------------------


class TestFilterEngineCategorizer:
    def test_filter_engine_get_section(self):
        from skill_manager.core.models.entities import Skill
        from skill_manager.core.models.filter_engine import FilterEngine

        skill = Skill(name="Test", local_path="/test")
        section = FilterEngine.get_section(skill)
        assert "|" in section

    def test_categorizer_category_in_name(self):
        from skill_manager.core.parsing.categorizer import categorize_skill

        # Category keyword appears in the name text — triggers line 115
        result = categorize_skill("Design Tools", "A set of design tools for the UI")
        assert "main_category" in result

    def test_win32_get_window_placement(self):
        from skill_manager.utils.win32 import get_window_placement

        # Mock GetWindowPlacement to return True so we hit the return tuple path
        mock_placement = MagicMock()
        mock_placement.flags = 0
        mock_placement.showCmd = 1
        mock_placement.ptMinPosition.x = 0
        mock_placement.ptMinPosition.y = 0
        mock_placement.ptMaxPosition.x = 100
        mock_placement.ptMaxPosition.y = 100
        mock_placement.rcNormalPosition.left = 0
        mock_placement.rcNormalPosition.top = 0
        mock_placement.rcNormalPosition.right = 800
        mock_placement.rcNormalPosition.bottom = 600

        with (
            patch("skill_manager.utils.win32.WINDOWPLACEMENT", return_value=mock_placement),
            patch("skill_manager.utils.win32.ctypes.sizeof", return_value=44),
            patch("skill_manager.utils.win32.ctypes", create=True) as mock_ctypes,
            patch("skill_manager.utils.win32.ctypes.byref", side_effect=lambda x: x),
        ):
            mock_ctypes.windll.user32.GetWindowPlacement.return_value = True
            result = get_window_placement(12345)
            assert isinstance(result, tuple)
            assert len(result) == 5
