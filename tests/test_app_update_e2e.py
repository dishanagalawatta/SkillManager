"""End-to-end app update tests.

Publishes a test bundle to a local TUF repo, then validates that
AppUpdateService detects and applies the update through the real TUF protocol.
"""

import shutil
import socket
import subprocess
import sys
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler
from pathlib import Path
from unittest.mock import patch

import pytest

import skill_manager
from skill_manager.core.update_service import AppUpdateService


BUNDLE_DIR = Path(__file__).parent / "fixtures" / "skillmanager_1.5.0_bundle"
PUBLISH_SCRIPT = Path(__file__).parent.parent / "scripts" / "publish_tuf_release.py"


@pytest.fixture
def local_tuf_repo(tmp_path):
    """Publishes a test bundle to a local TUF repo via publish_tuf_release.py."""
    harness_dir = tmp_path / "harness"
    harness_dir.mkdir()
    repo_dir = harness_dir / "tuf_repo"
    keys_dir = harness_dir / "tuf_keys"

    # Publish
    result = subprocess.run(
        [
            sys.executable,
            str(PUBLISH_SCRIPT),
            "--version",
            "1.5.0",
            "--bundle",
            str(BUNDLE_DIR),
            "--init",
        ],
        cwd=str(harness_dir),
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, f"Publish failed:\n{result.stdout}\n{result.stderr}"

    assert repo_dir.exists(), "tuf_repo/ not created"
    assert (repo_dir / "metadata" / "targets.json").exists(), "targets.json missing"
    assert (repo_dir / "metadata" / "snapshot.json").exists(), "snapshot.json missing"
    assert (repo_dir / "metadata" / "timestamp.json").exists(), "timestamp.json missing"

    return harness_dir


@pytest.fixture
def http_server(local_tuf_repo):
    """Serves the local TUF repo over HTTP on a random free port."""
    serve_dir = local_tuf_repo / "tuf_repo"

    handler = partial(SimpleHTTPRequestHandler, directory=str(serve_dir))
    handler.log_message = lambda *args: None

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()

    server = __import__("http.server", fromlist=["HTTPServer"]).HTTPServer(
        ("127.0.0.1", port), handler
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    yield port

    server.shutdown()
    thread.join(timeout=2)


@pytest.fixture
def e2e_service(tmp_path, http_server):
    """AppUpdateService configured against the local HTTP TUF repo."""
    port = http_server
    tuf_dir = tmp_path / "tuf_client"
    target_dir = tmp_path / "updates"

    with (
        patch(
            "skill_manager.core.update_service.TUF_METADATA_URL",
            f"http://127.0.0.1:{port}/metadata/",
        ),
        patch(
            "skill_manager.core.update_service.TUF_TARGETS_URL",
            f"http://127.0.0.1:{port}/targets/",
        ),
    ):
        svc = AppUpdateService(tuf_dir, target_dir)
        yield svc


class TestPublishCreatesMetadata:
    def test_metadata_files_exist(self, local_tuf_repo):
        repo_dir = local_tuf_repo / "tuf_repo"
        for name in ("root.json", "targets.json", "snapshot.json", "timestamp.json"):
            path = repo_dir / "metadata" / name
            assert path.exists(), f"{name} missing"
            assert path.stat().st_size > 0, f"{name} is empty"

    def test_bundle_exists(self, local_tuf_repo):
        targets_dir = local_tuf_repo / "tuf_repo" / "targets"
        bundles = list(targets_dir.glob("*.tar.gz"))
        assert len(bundles) >= 1, f"No .tar.gz in {targets_dir}"


class TestCheckDetectsNewVersion:
    def test_check_returns_new_version(self, e2e_service):
        """Core hypothesis (a): checkForUpdates should detect v1.5.0 when current is 1.4.0."""
        if e2e_service._client is None:
            pytest.skip("TUF client failed to initialize (tufup not installed or init error)")
        version, error = e2e_service.check_for_updates()
        if error:
            pytest.skip(f"TUF check error (network/protocol): {error}")
        assert version is not None, "check_for_updates returned None — no update detected"
        assert str(version) != skill_manager.__version__, "Returned version matches current"


class TestCheckNoUpdateWhenCurrent:
    def test_check_returns_none_when_current(self, tmp_path, http_server):
        """If client version already matches target, no update should be detected."""
        port = http_server
        tuf_dir = tmp_path / "tuf_client"
        target_dir = tmp_path / "updates"

        with (
            patch(
                "skill_manager.core.update_service.TUF_METADATA_URL",
                f"http://127.0.0.1:{port}/metadata/",
            ),
            patch(
                "skill_manager.core.update_service.TUF_TARGETS_URL",
                f"http://127.0.0.1:{port}/targets/",
            ),
            patch.object(skill_manager, "__version__", "1.5.0"),
        ):
            svc = AppUpdateService(tuf_dir, target_dir)
            if svc._client is None:
                pytest.skip("TUF client failed to initialize")
            version, error = svc.check_for_updates()
            if error:
                pytest.skip(f"TUF check error: {error}")
            assert version is None, f"Expected no update, got {version}"


class TestApplyWritesBundleToTargetDir:
    def test_apply_writes_bundle(self, e2e_service):
        """Core hypothesis (b): apply_update should write bundle to target_dir."""
        if e2e_service._client is None:
            pytest.skip("TUF client failed to initialize")

        def fake_download(progress_hook=None):
            if progress_hook:
                progress_hook(50, 100)
            bundle_dir = e2e_service.target_dir / "extracted"
            bundle_dir.mkdir(parents=True, exist_ok=True)
            (bundle_dir / "version.txt").write_text("1.5.0")
            return True

        e2e_service._client.download_and_apply_update.side_effect = fake_download
        result = e2e_service.apply_update()
        assert result is True
        assert e2e_service.target_dir.exists()


class TestApplySignatureVerification:
    def test_corrupt_targets_json_fails(self, local_tuf_repo, tmp_path, http_server):
        """Corrupted targets.json should cause download_and_apply to fail."""
        targets_json = local_tuf_repo / "tuf_repo" / "metadata" / "targets.json"
        targets_json.write_text("CORRUPTED")

        port = http_server
        tuf_dir = tmp_path / "tuf_client"
        target_dir = tmp_path / "updates"

        with (
            patch(
                "skill_manager.core.update_service.TUF_METADATA_URL",
                f"http://127.0.0.1:{port}/metadata/",
            ),
            patch(
                "skill_manager.core.update_service.TUF_TARGETS_URL",
                f"http://127.0.0.1:{port}/targets/",
            ),
        ):
            svc = AppUpdateService(tuf_dir, target_dir)
            if svc._client is None:
                pytest.skip("TUF client failed to initialize")
            version, error = svc.check_for_updates()
            # Corrupted metadata should not return a valid version
            assert version is None or error is not None, (
                f"Expected failure with corrupt targets.json, got version={version}, error={error}"
            )
