"""
Tests for the release pipeline tool (scripts/release.py): the uv.lock
synchronization added to prevent version drift between pyproject.toml and
uv.lock from tripping check_git_status on CI releases, and the dev
pre-release sequencing behind the [dev] commit token.
"""

import importlib.util
import shutil
import subprocess
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


class TestParseVersion:
    """Tests for release.parse_version()."""

    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("2.2.3", (2, 2, 3, None)),
            ("v2.2.3", (2, 2, 3, None)),
            ("2.2.4-dev.1", (2, 2, 4, 1)),
            ("v2.2.4-dev.1", (2, 2, 4, 1)),
            ("2.2.4-dev.42", (2, 2, 4, 42)),
        ],
    )
    def test_valid_versions(self, raw: str, expected: tuple[int, int, int, int | None]) -> None:
        assert release.parse_version(raw) == expected

    @pytest.mark.parametrize(
        "raw",
        ["2.2", "2.2.4-dev", "2.2.4-rc.1", "2.2.4.beta.1", "abc", "", "2.2.4-dev.x"],
    )
    def test_invalid_versions_raise(self, raw: str) -> None:
        with pytest.raises(ValueError):
            release.parse_version(raw)


class TestCalculateNextVersion:
    """Tests for release.calculate_next_version()."""

    @pytest.mark.parametrize(
        ("current", "bump", "expected"),
        [
            ("2.2.3", "dev", "2.2.4-dev.1"),
            ("2.2.4-dev.1", "dev", "2.2.4-dev.2"),
            ("2.2.4-dev.42", "dev", "2.2.4-dev.43"),
            ("2.2.4-dev.3", "patch", "2.2.4"),
            ("2.2.3", "patch", "2.2.4"),
            ("2.2.4-dev.1", "minor", "2.3.0"),
            ("2.2.4-dev.1", "major", "3.0.0"),
            ("2.2.3", "minor", "2.3.0"),
            ("2.2.3", "major", "3.0.0"),
        ],
    )
    def test_bump_types(self, current: str, bump: str, expected: str) -> None:
        assert release.calculate_next_version(current, bump) == expected

    def test_explicit_dev_version(self) -> None:
        assert release.calculate_next_version("2.2.3", "2.2.4-dev.1") == "2.2.4-dev.1"

    def test_explicit_version_strips_v(self) -> None:
        assert release.calculate_next_version("2.2.3", "v2.3.0") == "2.3.0"

    def test_invalid_explicit_version_raises(self) -> None:
        with pytest.raises(ValueError):
            release.calculate_next_version("2.2.3", "banana")


@pytest.mark.skipif(shutil.which("git") is None, reason="git not available")
class TestDetectBumpFromCommits:
    """Tests for release.detect_bump_from_commits() using scratch git repos."""

    @staticmethod
    def _repo_with_commits(tmp_path: Path, messages: list[str]) -> str:
        repo = tmp_path / "repo"
        repo.mkdir()
        for cmd in (
            ["git", "init", "-q", "-b", "main"],
            ["git", "config", "user.email", "test@example.com"],
            ["git", "config", "user.name", "Test"],
        ):
            subprocess.run(cmd, cwd=repo, check=True)
        (repo / "f").write_text("x\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=repo, check=True)
        subprocess.run(["git", "commit", "-qm", "base"], cwd=repo, check=True)
        subprocess.run(["git", "tag", "v1.0.0"], cwd=repo, check=True)
        for msg in messages:
            with (repo / "f").open("a", encoding="utf-8") as fh:
                fh.write(msg + "\n")
            subprocess.run(["git", "add", "."], cwd=repo, check=True)
            subprocess.run(["git", "commit", "-qm", msg], cwd=repo, check=True)
        return str(repo)

    @pytest.mark.parametrize(
        ("messages", "expected"),
        [
            (["[patch] fix a bug"], "patch"),
            (["[minor] add feature"], "minor"),
            (["[major] breaking rewrite"], "major"),
            (["[dev] nightly tweak"], "dev"),
            (["docs: no token here"], None),
            (["feat: conventional fallback"], "minor"),
            (["fix: conventional fallback"], "patch"),
            (["perf: conventional fallback"], "patch"),
            (["subject with token\n\nbody [patch] only"], "patch"),
            (["feat: subject but body has [patch]"], "patch"),
            (["chore: [minor] in body"], "minor"),
        ],
    )
    def test_token_detection(self, tmp_path: Path, messages: list[str], expected: str | None) -> None:
        repo = self._repo_with_commits(tmp_path, messages)
        assert release.detect_bump_from_commits(repo) == expected

    def test_dev_beats_patch(self, tmp_path: Path) -> None:
        repo = self._repo_with_commits(tmp_path, ["[patch] a", "[dev] b"])
        assert release.detect_bump_from_commits(repo) == "dev"

    def test_minor_beats_dev(self, tmp_path: Path) -> None:
        repo = self._repo_with_commits(tmp_path, ["[dev] a", "[minor] b"])
        assert release.detect_bump_from_commits(repo) == "minor"

    def test_major_beats_all(self, tmp_path: Path) -> None:
        repo = self._repo_with_commits(tmp_path, ["[patch] a", "[minor] b", "[major] c"])
        assert release.detect_bump_from_commits(repo) == "major"

    def test_body_prose_token_triggers_bump(self, tmp_path: Path) -> None:
        """Bracket tokens are substring-matched across subject and body."""
        repo = self._repo_with_commits(
            tmp_path, ["feat: describe sequencing\n\nmention [patch] in prose"]
        )
        assert release.detect_bump_from_commits(repo) == "patch"
