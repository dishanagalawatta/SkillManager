import os
import shutil
import sys
import tempfile
import uuid
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from PySide6.QtGui import QGuiApplication

from skill_manager.utils.task_runner import SynchronousTaskRunner

# Global test configuration
os.environ["SKILL_MANAGER_TESTING"] = "1"
os.environ["POSTHOG_PROJECT_TOKEN"] = ""
os.environ["POSTHOG_HOST"] = ""
os.environ["SKILL_MANAGER_SKIP_INITIAL_LOAD"] = "1"

os.environ.setdefault(
    "SKILL_MANAGER_DATA_DIR",
    str(Path(tempfile.gettempdir()) / f"skillmanager-pytest-{uuid.uuid4().hex}" / "data"),
)

# Automatically add 'src' to PYTHONPATH for all tests
src_path = str(Path(__file__).parent.parent / "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)


@pytest.fixture(scope="session")
def qapp():
    """Provides a QGuiApplication instance for the test session."""
    app = QGuiApplication.instance()
    if app is None:
        # Use offscreen platform for headless environments
        if os.environ.get("QT_QPA_PLATFORM") != "offscreen":
            os.environ["QT_QPA_PLATFORM"] = "offscreen"
        app = QGuiApplication([])
    yield app


@pytest.fixture
def temp_dir():
    """Provides a temporary directory that is automatically cleaned up."""
    path = Path(tempfile.gettempdir()) / f"skillmanager-test-{uuid.uuid4().hex}"
    path.mkdir(parents=True)
    yield path
    shutil.rmtree(path, ignore_errors=True)


@pytest.fixture
def mock_config(temp_dir):
    """Sets up a mock environment with a temporary data directory."""
    data_dir = temp_dir / "data"
    data_dir.mkdir()
    os.environ["SKILL_MANAGER_DATA_DIR"] = str(data_dir)
    yield data_dir
    os.environ.pop("SKILL_MANAGER_DATA_DIR", None)


@pytest.fixture
def mock_app():
    """Provides a shared mock for AppController with common attributes."""
    app = MagicMock()
    app.task_runner = SynchronousTaskRunner()
    # Core state
    app._selected_skill = {}
    app._archive_paths = []
    app._starred_paths = []
    app._is_loading = False
    app._status_message = ""
    app._sources = []
    app._projects = []
    app._update_sources = []
    app._syncing_projects = []
    app._project_aliases = {}
    app._update_results = []

    # Models
    app._library_model = MagicMock()
    app._quick_copy_model = MagicMock()
    app.skillModel = MagicMock()

    # Dependencies
    app._config = MagicMock()
    app._clipboard = MagicMock()

    # Common methods
    app._set_status = MagicMock()
    app.refreshSkills = MagicMock()
    app.load_initial_data = MagicMock()
    app.getProjectLabel.side_effect = lambda t: t.split("/")[-1] if t else ""

    return app


@pytest.fixture
def skill_factory():
    def _make_skill(**overrides):
        base = {
            "id": "test-id",
            "name": "Test Skill",
            "category": "Dev",
            "local_path": "/path/to/skill",
            "is_selected": False,
            "is_starred": False,
            "is_source": True,
            "project_label": "Master Library",
        }
        base.update(overrides)
        return base

    return _make_skill


@pytest.fixture
def source_factory():
    def _make_source(**overrides):
        base = {
            "name": "Test Source",
            "source_type": "git",
            "repository_url": "https://github.com/test/repo",
            "local_path": "/local/repo",
        }
        base.update(overrides)
        return base

    return _make_source
