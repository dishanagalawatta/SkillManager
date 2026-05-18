import sys

from skill_manager.core.resources import logo_asset_for_client, qml_components_dir, resource_path


def test_logo_asset_for_client_variants():
    assert logo_asset_for_client("Antigravity") == "clients/antigravity.svg"
    assert logo_asset_for_client("Gemini CLI") == "clients/gemini-cli.svg"
    assert logo_asset_for_client("Codex") == "clients/codex.svg"
    assert logo_asset_for_client("Plain Text") == "clients/plaintext.svg"
    assert logo_asset_for_client("Other") == "brand/logo.png"
    assert logo_asset_for_client(None) == "brand/logo.png"


def test_resource_path_uses_explicit_base():
    # Test with forward slashes for cross-platform comparison
    path = resource_path("assets/logo.png", base_path="C:/tmp/app").replace("\\", "/")
    assert path == "C:/tmp/app/assets/logo.png"


def test_qml_components_dir_dev_and_frozen(tmp_path):
    # Dev mode: uses package_file location
    package_file = tmp_path / "src" / "skill_manager" / "resources.py"
    package_file.parent.mkdir(parents=True)
    package_file.write_text("")
    assert qml_components_dir(frozen=False, package_file=str(package_file)) == (
        package_file.parent / "SkillManagerComponents"
    )

    # Frozen mode: uses meipass
    frozen_root = tmp_path / "bundle"
    internal = frozen_root / "_internal"
    internal.mkdir(parents=True)
    assert qml_components_dir(frozen=True, meipass=str(frozen_root)) == (
        internal / "skill_manager" / "SkillManagerComponents"
    )

    # Fallback for frozen mode without _internal (Windows)
    if sys.platform == "win32":
        fallback_root = tmp_path / "bundle-no-internal"
        assert qml_components_dir(frozen=True, meipass=str(fallback_root)) == (
            fallback_root / "skill_manager" / "SkillManagerComponents"
        )


def test_resource_path_default_base():
    # This is harder to test without mocking sys._MEIPASS
    # but we can verify it doesn't crash
    path = resource_path("test.txt")
    assert path.endswith("test.txt")
