import pytest
import os
import shutil
import tempfile
import uuid
from pathlib import Path
from PySide6.QtGui import QGuiApplication

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
def skill_factory():
    def _make_skill(**overrides):
        base = {
            "id": "test-id",
            "name": "Test Skill",
            "category": "Dev",
            "local_path": "/path/to/skill",
            "is_selected": False,
            "is_essential": False,
            "is_source": True,
            "project_label": "Master Library"
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
            "local_path": "/local/repo"
        }
        base.update(overrides)
        return base
    return _make_source
