"""
Tests for the release pipeline tool (scripts/release.py): the uv.lock
synchronization added to prevent version drift between pyproject.toml and
uv.lock from tripping check_git_status on release, and the dev
pre-release sequencing behind the `dev` bump.
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
        with (
            patch.object(release.subprocess, "run", return_value=mock_result) as mock_run,
            pytest.raises(SystemExit) as exc_info,
        ):
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
        with (
            patch.object(release.subprocess, "run", return_value=mock_result),
            pytest.raises(SystemExit) as exc_info,
        ):
            release.sync_uvlock(str(project_root), "2.2.1")
        assert exc_info.value.code == 1

    def test_accepts_canonical_pep440_dev_form(self, project_root: Path) -> None:
        """uv canonicalizes pre-releases in the lockfile: 2.2.5-dev.1 -> 2.2.5.dev1."""

        def fake_uv_lock(*args, **kwargs):  # noqa: ARG001
            updated = LOCKFILE_HEADER.replace('version = "2.2.0"', 'version = "2.2.5.dev1"')
            (project_root / "uv.lock").write_text(updated, encoding="utf-8")
            return type("R", (), {"returncode": 0, "stderr": ""})

        with patch.object(release.subprocess, "run", side_effect=fake_uv_lock):
            release.sync_uvlock(str(project_root), "2.2.5-dev.1")
        assert 'version = "2.2.5.dev1"' in (project_root / "uv.lock").read_text(encoding="utf-8")


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


class TestGitIdentityGuard:
    """Release must fail before syncing files when git identity is missing."""

    def test_missing_identity_exits(self, tmp_path: Path, capsys) -> None:
        result = type("R", (), {"returncode": 1, "stdout": "", "stderr": "fatal"})
        with (
            patch.object(release.subprocess, "run", return_value=result),
            pytest.raises(SystemExit) as exc_info,
        ):
            release.check_git_identity(str(tmp_path))
        assert exc_info.value.code == 1
        out = capsys.readouterr().out
        assert 'git config user.email "you@example.com"' in out

    def test_configured_identity_passes(self, tmp_path: Path) -> None:
        result = type(
            "R",
            (),
            {"returncode": 0, "stdout": "Dikka <dikka@example.com> 1 +0000\n", "stderr": ""},
        )
        with patch.object(release.subprocess, "run", return_value=result):
            release.check_git_identity(str(tmp_path))  # must not raise

    def test_identity_checked_before_version_sync(self, tmp_path: Path, monkeypatch) -> None:
        calls: list[str] = []
        monkeypatch.setattr(release.sys, "argv", ["release.py", "patch"])
        monkeypatch.setattr(release, "get_project_root", lambda: str(tmp_path))
        monkeypatch.setattr(release, "get_current_version", lambda root: "2.13.2")
        monkeypatch.setattr(release, "check_git_status", lambda root: calls.append("status"))
        monkeypatch.setattr(release, "check_git_identity", lambda root: calls.append("identity"))
        monkeypatch.setattr(release, "run_preflight_checks", lambda *a: calls.append("preflight"))
        for name in (
            "sync_pyproject",
            "sync_uvlock",
            "sync_init_py",
            "sync_installer_iss",
            "sync_metainfo_xml",
            "sync_readme",
            "update_changelog",
            "prepare_release_pr",
        ):
            monkeypatch.setattr(release, name, lambda *a, **k: calls.append("sync"))

        release.main()

        assert calls[:3] == ["status", "identity", "preflight"]
        assert "sync" in calls
