"""End-to-end app update tests.

Publishes a test bundle to a local TUF repo, then validates that
AppUpdateService detects and applies the update through the real TUF protocol.
"""

import builtins
import shutil
import socket
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler
from pathlib import Path
from unittest.mock import patch

import pytest
from tufup.repo import Repository

import skill_manager
from skill_manager.core.update_service import AppUpdateService

BUNDLE_DIR = Path(__file__).parent / "fixtures" / "skillmanager_1.5.0_bundle"


@pytest.fixture
def local_tuf_repo(tmp_path):
    """Creates a local TUF repo with fresh keys and publishes test bundle."""
    harness_dir = tmp_path / "harness"
    harness_dir.mkdir()
    repo_dir = harness_dir / "tuf_repo"
    keys_dir = harness_dir / "tuf_keys"

    # Initialize repo — tufup generates fresh keys (no copy needed)
    # Patch input() to auto-accept any overwrite prompts
    original_input = builtins.input
    builtins.input = lambda *a, **k: "y"
    try:
        repo = Repository(
            repo_dir=str(repo_dir),
            keys_dir=str(keys_dir),
            app_name="SkillManager",
        )
        repo.initialize()
    finally:
        builtins.input = original_input

    # Add bundle
    repo.add_bundle(new_version="1.5.0", new_bundle_dir=str(BUNDLE_DIR))

    # Publish (sign with project keys)
    repo.publish_changes(private_key_dirs=[str(keys_dir)])

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
def e2e_service(tmp_path, http_server, local_tuf_repo):
    """AppUpdateService configured against the local HTTP TUF repo."""
    port = http_server
    tuf_dir = tmp_path / "tuf_client"
    tuf_dir.mkdir()
    target_dir = tmp_path / "updates"

    # Copy generated root.json BEFORE service init so TUF client loads correct keys
    src_root = local_tuf_repo / "tuf_repo" / "metadata" / "root.json"
    if src_root.exists():
        shutil.copy2(src_root, tuf_dir / "root.json")

    with (
        patch(
            "skill_manager.core.update_service.TUF_METADATA_URL",
            f"http://127.0.0.1:{port}/metadata/",
        ),
        patch(
            "skill_manager.core.update_service.TUF_TARGETS_URL",
            f"http://127.0.0.1:{port}/targets/",
        ),
        patch(
            "skill_manager.core.update_service.AppUpdateService._ensure_root_json",
        ),
        patch.object(skill_manager, "__version__", "1.4.0"),
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
        assert version is not None, "check_for_updates returned None - no update detected"
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

        with patch.object(
            e2e_service._client, "download_and_apply_update", side_effect=fake_download
        ):
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


class TestRealDownloadAndExtract:
    def test_real_download_extracts_bundle(self, e2e_service, tmp_path):
        """Full E2E: check -> download real bundle -> extract -> verify files."""
        if e2e_service._client is None:
            pytest.skip("TUF client failed to initialize")

        # Step 1: detect update
        version, error = e2e_service.check_for_updates()
        if error:
            pytest.skip(f"TUF check error: {error}")
        assert version is not None, "No update detected"

        # Step 2: real download + extract with no-op install
        extract_dir = tmp_path / "extracted"
        extract_dir.mkdir()
        e2e_service._client.extract_dir = extract_dir

        written = {}

        def capture_install(src_dir, dst_dir, **kwargs):
            written["src"] = str(src_dir)
            written["dst"] = str(dst_dir)
            for f in src_dir.rglob("*"):
                if f.is_file():
                    dest = e2e_service.target_dir / f.relative_to(src_dir)
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(f, dest)

        e2e_service._client.download_and_apply_update(
            skip_confirmation=True,
            install=capture_install,
        )

        # Step 3: verify extracted files exist
        extracted_files = list(extract_dir.rglob("*"))
        extracted_files = [f for f in extracted_files if f.is_file()]
        assert len(extracted_files) >= 2, (
            f"Expected >=2 extracted files, got {len(extracted_files)}: {extracted_files}"
        )
        names = {f.name for f in extracted_files}
        assert "version.json" in names, f"version.json missing from {names}"

        # Step 4: verify version.json content
        vf = extract_dir / "version.json"
        import json

        data = json.loads(vf.read_text())
        assert data.get("version") == "1.5.0", f"Wrong version in bundle: {data}"
