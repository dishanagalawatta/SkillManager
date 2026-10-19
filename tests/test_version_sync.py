"""
Unit tests for version consistency across metadata files and release synchronization logic.
"""

import os
import re
import sys

import pytest

# Add scripts directory to path to import release functions
SCRIPTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

from release import (  # noqa: E402
    calculate_next_version,
    get_current_version,
    get_project_root,
    parse_version,
)

import skill_manager  # noqa: E402


def _load_windows_version_info():
    """Import ``packaging/windows/version_info.py`` without touching sys.path.

    That directory sits under a folder named ``packaging``, which collides with
    the widely used PyPI distribution of the same name that PyInstaller and other
    build tooling import. Adding it to sys.path would shadow that package, so the
    file is loaded by path instead.
    """
    import importlib.util

    path = os.path.join(get_project_root(), "packaging", "windows", "version_info.py")
    spec = importlib.util.spec_from_file_location("_sm_version_info_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_semver_parsing():
    """Test semantic version parsing helper (4-tuple: major, minor, patch, dev)."""
    assert parse_version("1.9.0") == (1, 9, 0, None)
    assert parse_version("v1.9.0") == (1, 9, 0, None)
    assert parse_version("2.0.15") == (2, 0, 15, None)
    assert parse_version("2.2.5-dev.1") == (2, 2, 5, 1)

    with pytest.raises(ValueError, match="Invalid version format"):
        parse_version("1.9")

    with pytest.raises(ValueError, match="Invalid version format"):
        parse_version("alpha.1")


def test_calculate_next_version():
    """Test bump calculations for patch, minor, major, and explicit versions."""
    assert calculate_next_version("1.9.0", "patch") == "1.9.1"
    assert calculate_next_version("1.9.0", "minor") == "1.10.0"
    assert calculate_next_version("1.9.0", "major") == "2.0.0"
    assert calculate_next_version("1.9.0", "2.0.5") == "2.0.5"
    assert calculate_next_version("1.9.0", "v2.0.5") == "2.0.5"


def test_version_consistency_across_metadata():
    """
    Verify that all repository files with version metadata are strictly synchronized
    with pyproject.toml (the single source of truth).
    """
    root = get_project_root()
    expected_version = get_current_version(root)

    # 1. Python package __version__
    assert skill_manager.__version__ == expected_version, (
        f"skill_manager.__version__ ({skill_manager.__version__}) != pyproject.toml ({expected_version})"
    )

    # 2. Inno Setup installer script
    iss_path = os.path.join(root, "packaging", "windows", "installer.iss")
    if os.path.exists(iss_path):
        with open(iss_path, encoding="utf-8") as f:
            iss_content = f.read()
        iss_match = re.search(r'#define\s+MyAppVersion\s+"([^"]+)"', iss_content)
        assert iss_match is not None, "MyAppVersion not found in installer.iss"
        assert iss_match.group(1) == expected_version, (
            f"installer.iss ({iss_match.group(1)}) != pyproject.toml ({expected_version})"
        )

    # 3. Linux AppStream metainfo XML
    metainfo_path = os.path.join(
        root, "packaging", "linux", "org.dishanagalawatta.SkillManager.metainfo.xml"
    )
    if os.path.exists(metainfo_path):
        with open(metainfo_path, encoding="utf-8") as f:
            xml_content = f.read()
        assert f'<release version="{expected_version}"' in xml_content, (
            f"Metainfo XML does not contain current release version {expected_version}"
        )

    # 4. Windows version resource, generated at build time for the EXE metadata
    version_info = _load_windows_version_info()
    assert version_info.resolve_version(root) == expected_version, (
        "version_info.resolve_version() disagrees with get_current_version()"
    )
    resource = version_info.build_version_file(expected_version)
    for attribute, value in (
        ("ProductName", "SkillManager"),
        ("ProductVersion", expected_version),
        ("FileVersion", expected_version),
    ):
        assert f'StringStruct("{attribute}", "{value}")' in resource, (
            f"generated version resource is missing {attribute}={value}"
        )


def test_windows_version_tuple_pads_and_drops_prerelease():
    """The file-version tuple is numeric-only and always four parts."""
    version_info = _load_windows_version_info()
    assert version_info.version_tuple("2.12.1") == (2, 12, 1, 0)
    assert version_info.version_tuple("v2.12.1") == (2, 12, 1, 0)
    assert version_info.version_tuple("2.13.0-dev.3") == (2, 13, 0, 0)

    with pytest.raises(ValueError, match="Cannot derive"):
        version_info.version_tuple("nightly")


def test_windows_version_resource_is_evaluable():
    """PyInstaller eval's this text, so a typo would otherwise surface on Windows.

    The names PyInstaller injects are stubbed here purely to prove the generated
    expression parses and calls them in a valid shape.
    """

    class _Stub:
        def __init__(self, *args, **kwargs):
            pass

    namespace = dict.fromkeys(
        (
            "VSVersionInfo",
            "FixedFileInfo",
            "StringFileInfo",
            "StringTable",
            "StringStruct",
            "VarFileInfo",
            "VarStruct",
        ),
        _Stub,
    )
    evaluated = eval(_load_windows_version_info().build_version_file("2.12.1"), namespace)
    assert isinstance(evaluated, _Stub)


def test_detect_bump_from_commits(monkeypatch):
    """Test commit log parsing for release triggers across subject and body."""
    from release import detect_bump_from_commits

    class MockCompletedProcess:
        def __init__(self, stdout: str):
            self.stdout = stdout

    # Case 1: [minor] in body
    def mock_run_minor(cmd, **kwargs):
        if "describe" in cmd:
            return MockCompletedProcess("v1.9.0\n")
        return MockCompletedProcess(
            "feat: update docs\n\nSome body text with [minor] tag inside.\n---COMMIT-DELIMITER---\n"
        )

    monkeypatch.setattr("subprocess.run", mock_run_minor)
    assert detect_bump_from_commits("/dummy") == "minor"

    # Case 2: [patch] in subject with feat: prefix (explicit [patch] overrides feat: prefix)
    def mock_run_patch_override(cmd, **kwargs):
        if "describe" in cmd:
            return MockCompletedProcess("v2.0.0\n")
        return MockCompletedProcess(
            "feat: enhance installer script to manage desktop entries [patch]\n---COMMIT-DELIMITER---\n"
        )

    monkeypatch.setattr("subprocess.run", mock_run_patch_override)
    assert detect_bump_from_commits("/dummy") == "patch"

    # Case 3: [minor] overriding fix: prefix
    def mock_run_minor_override(cmd, **kwargs):
        if "describe" in cmd:
            return MockCompletedProcess("v2.0.0\n")
        return MockCompletedProcess(
            "fix: resolve bug and expand subsystem [minor]\n---COMMIT-DELIMITER---\n"
        )

    monkeypatch.setattr("subprocess.run", mock_run_minor_override)
    assert detect_bump_from_commits("/dummy") == "minor"

    # Case 4: [major] in body
    def mock_run_major(cmd, **kwargs):
        if "describe" in cmd:
            return MockCompletedProcess("v2.0.0\n")
        return MockCompletedProcess(
            "chore: database overhaul\n\nbreaking change: schema changed [major]\n---COMMIT-DELIMITER---\n"
        )

    monkeypatch.setattr("subprocess.run", mock_run_major)
    assert detect_bump_from_commits("/dummy") == "major"

    # Case 5: Conventional commit fallback (feat: without token -> minor)
    def mock_run_feat_fallback(cmd, **kwargs):
        if "describe" in cmd:
            return MockCompletedProcess("v2.0.0\n")
        return MockCompletedProcess("feat: add new search filter\n---COMMIT-DELIMITER---\n")

    monkeypatch.setattr("subprocess.run", mock_run_feat_fallback)
    assert detect_bump_from_commits("/dummy") == "minor"

    # Case 6: Conventional commit fallback (fix: without token -> patch)
    def mock_run_fix_fallback(cmd, **kwargs):
        if "describe" in cmd:
            return MockCompletedProcess("v2.0.0\n")
        return MockCompletedProcess("fix: resolve crash on shutdown\n---COMMIT-DELIMITER---\n")

    monkeypatch.setattr("subprocess.run", mock_run_fix_fallback)
    assert detect_bump_from_commits("/dummy") == "patch"

    # Case 7: No trigger tokens or prefixes
    def mock_run_none(cmd, **kwargs):
        if "describe" in cmd:
            return MockCompletedProcess("v2.0.0\n")
        return MockCompletedProcess("chore: update internal comments\n---COMMIT-DELIMITER---\n")

    monkeypatch.setattr("subprocess.run", mock_run_none)
    assert detect_bump_from_commits("/dummy") is None
