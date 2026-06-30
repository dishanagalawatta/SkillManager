"""Tests for rebuildCache() clearing both caches and resetting state."""
from unittest.mock import MagicMock, patch


def _make_app(tmp_path):
    """Helper to build a mock app with task_runner that runs synchronously."""
    app = MagicMock()
    app._set_status = MagicMock()
    app.loadInitialData = MagicMock()
    app.discovery = MagicMock()
    app.discovery._previous_skills = {}

    def _run_sync(fn, *args, **kwargs):
        return fn(*args, **kwargs)

    app.task_runner.run.side_effect = _run_sync
    return app


def test_rebuild_cache_clears_json_index(tmp_path):
    """rebuildCache() deletes the JSON index cache file."""
    from skill_manager.app import AppController

    json_cache = tmp_path / "skill_library_index.json"
    json_cache.write_text('{"skills": [], "categories": []}')

    app = _make_app(tmp_path)

    with patch("skill_manager.core.config.SKILL_LIBRARY_CACHE_FILE", str(json_cache)), \
         patch("skill_manager.app.os.path.exists", return_value=True), \
         patch("skill_manager.app.os.remove") as mock_remove:
        AppController.rebuildCache(app)

        mock_remove.assert_called_once_with(str(json_cache))


def test_rebuild_cache_clears_granular_diskcache(tmp_path):
    """rebuildCache() clears the granular diskcache directory."""
    from diskcache import Cache

    from skill_manager.app import AppController

    discovery_cache_dir = tmp_path / "cache" / "discovery"
    discovery_cache_dir.mkdir(parents=True)

    # Seed the diskcache
    dc = Cache(str(discovery_cache_dir))
    dc.set("test_key", "test_value")
    assert dc.get("test_key") == "test_value"
    dc.close()

    app = _make_app(tmp_path)

    with patch("skill_manager.core.config.SKILL_LIBRARY_CACHE_FILE", str(tmp_path / "nonexistent.json")), \
         patch("skill_manager.app.os.path.exists", return_value=False), \
         patch("skill_manager.core.discovery.get_discovery_cache") as mock_get_cache:
        mock_dc = Cache(str(discovery_cache_dir))
        mock_get_cache.return_value.__enter__ = lambda s: mock_dc
        mock_get_cache.return_value.__exit__ = MagicMock(return_value=False)

        AppController.rebuildCache(app)

        # Verify cleared
        dc2 = Cache(str(discovery_cache_dir))
        assert dc2.get("test_key") is None
        dc2.close()


def test_rebuild_cache_resets_previous_skills(tmp_path):
    """rebuildCache() resets _previous_skills so next discovery forces full diff."""
    from skill_manager.app import AppController

    app = _make_app(tmp_path)

    with patch("skill_manager.core.config.SKILL_LIBRARY_CACHE_FILE", str(tmp_path / "nonexistent.json")), \
         patch("skill_manager.app.os.path.exists", return_value=False):
        AppController.rebuildCache(app)

    assert app.discovery._previous_skills == {}


def test_rebuild_cache_triggers_load_initial_data(tmp_path):
    """rebuildCache() calls loadInitialData() to trigger re-discovery."""
    from skill_manager.app import AppController

    app = _make_app(tmp_path)

    with patch("skill_manager.core.config.SKILL_LIBRARY_CACHE_FILE", str(tmp_path / "nonexistent.json")), \
         patch("skill_manager.app.os.path.exists", return_value=False):
        AppController.rebuildCache(app)

    app.discovery.loadInitialData.assert_called_once_with(force_full_scan=True, silent=True)
