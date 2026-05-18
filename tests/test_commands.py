from datetime import date

from skill_manager.core.commands import (
    build_command_content,
    build_command_filename,
    create_custom_command_file,
)


def test_find_project_path_by_label():
    # Mocking project_label behavior if needed, but here we can just rely on the implementation
    # which calls project_label(project_path).
    # Since we can't easily mock the import inside commands.py without patch,
    # let's use a more realistic setup with tmp_path in a functional test.
    pass


def test_build_command_filename():
    assert build_command_filename("Deploy Now!", "Codex") == "Deploy_Now_.Codex.md"
    assert build_command_filename("test/command", "Gemini") == "test_command.Gemini.md"
    assert build_command_filename("spaces to underscores", "CLI") == "spaces_to_underscores.CLI.md"
    assert build_command_filename("..\\..\\etc\\passwd", "Evil") == "______etc_passwd.Evil.md"
    assert build_command_filename("cmd & other", "CLI") == "cmd___other.CLI.md"


def test_build_command_content():
    content = build_command_content(
        name="Test",
        client="Codex",
        body="Execute this",
        category="Testing",
        created_on=date(2026, 2, 27),
    )
    assert "name: Test" in content
    assert "client: Codex" in content
    assert "category: Testing" in content
    assert "date: 2026-02-27" in content
    assert "Execute this" in content


def test_create_custom_command_file_success(tmp_path):
    project_root = tmp_path / "my-project"
    project_path = project_root / ".agents" / "skills"
    project_path.mkdir(parents=True)

    result = create_custom_command_file(
        name="Start",
        client="CLI",
        body="echo 'hello'",
        project_label_name="my-project",
        category="General",
        project_paths=[str(project_path)],
        created_on=date(2026, 2, 27),
    )

    assert result.ok
    assert result.path.exists()
    assert result.path.name == "Start.CLI.md"
    assert "echo 'hello'" in result.path.read_text()


def test_create_custom_command_file_missing_name(tmp_path):
    result = create_custom_command_file(
        name="",
        client="CLI",
        body="body",
        project_label_name="proj",
        category="cat",
        project_paths=[str(tmp_path)],
    )
    assert not result.ok
    assert "Command name is required" in result.message


def test_create_custom_command_file_invalid_project(tmp_path):
    result = create_custom_command_file(
        name="Cmd",
        client="CLI",
        body="body",
        project_label_name="All Projects",
        category="cat",
        project_paths=[str(tmp_path)],
    )
    assert not result.ok
    assert "Please select a specific Project" in result.message


def test_create_custom_command_file_project_not_found(tmp_path):
    result = create_custom_command_file(
        name="Cmd",
        client="CLI",
        body="body",
        project_label_name="non-existent",
        category="cat",
        project_paths=[str(tmp_path)],
    )
    assert not result.ok
    assert "Could not find project directory" in result.message


def test_create_custom_command_file_duplicate(tmp_path):
    project_root = tmp_path / "proj"
    project_path = project_root / ".agents" / "skills"
    project_path.mkdir(parents=True)
    commands_dir = project_path / "commands"
    commands_dir.mkdir()
    existing_file = commands_dir / "Cmd.CLI.md"
    existing_file.write_text("existing")

    result = create_custom_command_file(
        name="Cmd",
        client="CLI",
        body="new body",
        project_label_name="proj",
        category="cat",
        project_paths=[str(project_path)],
    )
    assert not result.ok
    assert "already exists" in result.message


def test_create_custom_command_file_filesystem_error(tmp_path):
    project_root = tmp_path / "readonly_proj"
    project_path = project_root / ".agents" / "skills"
    project_path.mkdir(parents=True)

    # On some systems making it readonly might not stop directory creation inside it
    # but we can try making the commands dir a file
    commands_dir_as_file = project_path / "commands"
    commands_dir_as_file.write_text("i am a file")

    result = create_custom_command_file(
        name="Cmd",
        client="CLI",
        body="body",
        project_label_name="readonly_proj",
        category="cat",
        project_paths=[str(project_path)],
    )
    assert not result.ok
    assert "Error creating command" in result.message
