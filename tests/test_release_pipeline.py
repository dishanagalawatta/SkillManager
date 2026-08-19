"""
Tests for the release pipeline tool (scripts/release.py), specifically the
uv.lock synchronization added to prevent version drift between pyproject.toml
and uv.lock from tripping check_git_status on CI releases.
"""

import importlib.util
from pathlib import Path
from unittest.mock import patch

import pytest

RELEASE_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "release.py"

# Load scripts/release.py as a module (it only executes main() under __main__).
_spec = importlib.util.spec_from_file_location("release", RELEASE_SCRIPT)
assert _spec and _spec.loader
release = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(release)

LOCKFILE_HEADER = """version = 1
requires-python = ">=3.12"

[[package]]
name = "skill-manager"
version = "2.2.0"
source = {{ editable = "." }}
"""


@pytest.fixture()
def project_root(tmp_path: Path) -> Path:
    """Create a temp project dir containing a stale uv.lock."""
    (tmp_path / "uv.lock").write_text(LOCKFILE_HEADER, encoding="utf-8")
    return tmp_path


class TestSyncUvlock:
    """Tests for release.sync_uvlock()."""

    def test_missing_lockfile_is_noop(self, tmp_path: Path) -> None:
        """No uv.lock -> skip silently, no subprocess call."""
        with patch.object(release.subprocess, "run") as mock_run:
            release.sync_uvlock(str(tmp_path), "2.2.1")
        mock_run.assert_not_called()

    def test_dry_run_skips_execution(self, project_root: Path) -> None:
        """dry_run=True -> report intent only, no uv lock execution."""
        with patch.object(release.subprocess, "run") as mock_run:
            release.sync_uvlock(str(project_root), "2.2.1", dry_run=True)
        mock_run.assert_not_called()

    def test_uv_lock_failure_exits(self, project_root: Path) -> None:
        """uv lock returns non-zero -> SystemExit with error message."""
        mock_result = type("R", (), {"returncode": 1, "stderr": "resolution failed"})
        with patch.object(
            release.subprocess, "run", return_value=mock_result
        ) as mock_run, pytest.raises(SystemExit) as exc_info:
            release.sync_uvlock(str(project_root), "2.2.1")
        mock_run.assert_called_once()
        assert exc_info.value.code == 1

    def test_success_syncs_lockfile(self, project_root: Path) -> None:
        """uv lock converges -> guard passes, no exception."""

        def fake_uv_lock(*args, **kwargs):  # noqa: ARG001
            # Simulate uv rewriting the lockfile with the new version.
            updated = LOCKFILE_HEADER.replace('version = "2.2.0"', 'version = "2.2.1"')
            (project_root / "uv.lock").write_text(updated, encoding="utf-8")
            return type("R", (), {"returncode": 0, "stderr": ""})

        with patch.object(release.subprocess, "run", side_effect=fake_uv_lock):
            release.sync_uvlock(str(project_root), "2.2.1")
        assert (project_root / "uv.lock").read_text(encoding="utf-8").count("2.2.1") == 1

    def test_guard_detects_stale_lockfile(self, project_root: Path) -> None:
        """uv lock 'succeeds' but version did not converge -> SystemExit."""
        mock_result = type("R", (), {"returncode": 0, "stderr": ""})
        with patch.object(
            release.subprocess, "run", return_value=mock_result
        ), pytest.raises(SystemExit) as exc_info:
            release.sync_uvlock(str(project_root), "2.2.1")
        assert exc_info.value.code == 1


class TestReleaseModuleSanity:
    """Lightweight guards that the release pipeline wiring stays intact."""

    def test_sync_uvlock_is_wired_after_pyproject(self) -> None:
        """uv.lock must be regenerated after pyproject is bumped."""
        source = RELEASE_SCRIPT.read_text(encoding="utf-8")
        pyproject_call = source.index("sync_pyproject(project_root, next_ver")
        uvlock_call = source.index("sync_uvlock(project_root, next_ver")
        assert uvlock_call > pyproject_call

    def test_uvlock_staged_in_release_commit(self) -> None:
        """The release commit must include uv.lock."""
        source = RELEASE_SCRIPT.read_text(encoding="utf-8")
        assert '"uv.lock",' in source
