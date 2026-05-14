import pytest
import os
import shutil
import tempfile
import uuid
from pathlib import Path
from PySide6.QtCore import QCoreApplication

@pytest.fixture(scope="session")
def qapp():
    """Provides a QCoreApplication instance for the test session."""
    app = QCoreApplication.instance()
    if app is None:
        app = QCoreApplication([])
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
