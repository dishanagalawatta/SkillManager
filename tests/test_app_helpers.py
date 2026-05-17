import sys
from datetime import date

from skill_manager.core.categories import get_category_emoji
from skill_manager.core.commands import (
    build_command_content,
    build_command_filename,
    create_custom_command_file,
    find_target_for_project,
)
from skill_manager.core.resources import logo_asset_for_client, qml_components_dir, resource_path


def test_get_category_emoji_exact_case_insensitive_substring_and_fallback():
    assert get_category_emoji("Testing") == "🧪"
    assert get_category_emoji("testing") == "🧪"
    assert get_category_emoji("Advanced Web Development") == "🌐"
    assert get_category_emoji("**Security**") == "🛡️"
    assert get_category_emoji("") == "📁"
    assert get_category_emoji("Unknown Area") == "📁"


def test_logo_asset_for_client_variants():
    assert logo_asset_for_client("Antigravity") == "clients/antigravity.svg"
    assert logo_asset_for_client("Gemini CLI") == "clients/gemini-cli.svg"
    assert logo_asset_for_client("Codex") == "clients/codex.svg"
    assert logo_asset_for_client("Plain Text") == "clients/plaintext.svg"
    assert logo_asset_for_client("Other") == "brand/logo.png"


def test_resource_path_uses_explicit_base():
    assert resource_path("assets/logo.png", base_path="C:/tmp/app").replace("\\", "/") == (
        "C:/tmp/app/assets/logo.png"
    )


def test_qml_components_dir_dev_and_frozen(tmp_path):
    package_file = tmp_path / "src" / "skill_manager" / "resources.py"
    package_file.parent.mkdir(parents=True)
    package_file.write_text("")
    assert qml_components_dir(frozen=False, package_file=str(package_file)) == (
        package_file.parent / "SkillManagerComponents"
    )

    frozen_root = tmp_path / "bundle"
    internal = frozen_root / "_internal"
    internal.mkdir(parents=True)
    assert qml_components_dir(frozen=True, meipass=str(frozen_root)) == (
        internal / "skill_manager" / "SkillManagerComponents"
    )

    if sys.platform == "win32":
        fallback_root = tmp_path / "bundle-no-internal"
        assert qml_components_dir(frozen=True, meipass=str(fallback_root)) == (
            fallback_root / "skill_manager" / "SkillManagerComponents"
        )


def test_command_helpers_create_success_and_validate(tmp_path):
    target = tmp_path / "project" / ".agents" / "skills"
    target.mkdir(parents=True)

    assert find_target_for_project("project", [str(target)]) == target
    assert build_command_filename("Deploy Now!", "Codex") == "Deploy_Now_.Codex.md"
    assert "date: 2026-01-02" in build_command_content(
        "Deploy",
        "Codex",
        "run it",
        "Ops",
        date(2026, 1, 2),
    )

    missing_name = create_custom_command_file(
        name="",
        client="Codex",
        body="",
        project_label_name="project",
        category="Ops",
        targets=[str(target)],
    )
    assert not missing_name.ok
    assert missing_name.message == "Error: Command name is required"

    missing_project = create_custom_command_file(
        name="Deploy",
        client="Codex",
        body="",
        project_label_name="All Projects",
        category="Ops",
        targets=[str(target)],
    )
    assert not missing_project.ok
    assert missing_project.message == "Error: Please select a specific Project"

    created = create_custom_command_file(
        name="Deploy Now!",
        client="Codex",
        body="run it",
        project_label_name="project",
        category="Ops",
        targets=[str(target)],
        created_on=date(2026, 1, 2),
    )
    assert created.ok
    assert created.path.read_text(encoding="utf-8").endswith("run it")

    duplicate = create_custom_command_file(
        name="Deploy Now!",
        client="Codex",
        body="run it",
        project_label_name="project",
        category="Ops",
        targets=[str(target)],
    )
    assert not duplicate.ok
    assert "already exists" in duplicate.message


def test_command_create_missing_target(tmp_path):
    result = create_custom_command_file(
        name="Deploy",
        client="Codex",
        body="",
        project_label_name="missing",
        category="Ops",
        targets=[str(tmp_path)],
    )
    assert not result.ok
    assert result.message == "Error: Could not find target for missing"
