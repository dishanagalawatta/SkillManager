from datetime import date

from skill_manager.core.commands import (
    build_command_content,
    build_command_filename,
    create_custom_command_file,
    update_custom_command_file,
)


def test_find_project_path_by_label():
    pass


def test_build_command_filename():
    assert build_command_filename("Deploy Now!") == "Deploy_Now_.md"
    assert build_command_filename("test/command") == "test_command.md"
    assert build_command_filename("spaces to underscores") == "spaces_to_underscores.md"
    assert build_command_filename("..\\..\\etc\\passwd") == "______etc_passwd.md"
    assert build_command_filename("cmd & other") == "cmd___other.md"


def test_build_command_content():
    content = build_command_content(
        name="Test",
        body="Execute this",
        category="Testing",
        created_on=date(2026, 2, 27),
    )
    assert "name: Test" in content
    assert "client:" not in content
    assert "category: Testing" in content
    assert "date: 2026-02-27" in content
    assert "Execute this" in content


def test_create_custom_command_file_success(tmp_path):
    project_root = tmp_path / "my-project"
    project_path = project_root / ".agents" / "skills"
    project_path.mkdir(parents=True)
    commands_dir = project_root / ".agents" / "commands"

    result = create_custom_command_file(
        name="Start",
        body="echo 'hello'",
        project_label_name="my-project",
        category="General",
        project_paths=[str(project_path)],
        created_on=date(2026, 2, 27),
    )

    assert result.ok
    assert result.path == commands_dir / "Start.md"
    assert result.path.exists()
    assert result.path.name == "Start.md"
    assert "echo 'hello'" in result.path.read_text()


def test_create_custom_command_file_missing_name(tmp_path):
    result = create_custom_command_file(
        name="",
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
    commands_dir = project_root / ".agents" / "commands"
    commands_dir.mkdir(parents=True)
    existing_file = commands_dir / "Cmd.md"
    existing_file.write_text("existing")

    result = create_custom_command_file(
        name="Cmd",
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

    (project_root / ".agents").mkdir(parents=True, exist_ok=True)
    commands_dir_as_file = project_root / ".agents" / "commands"
    commands_dir_as_file.write_text("i am a file")

    result = create_custom_command_file(
        name="Cmd",
        body="body",
        project_label_name="readonly_proj",
        category="cat",
        project_paths=[str(project_path)],
    )
    assert not result.ok
    assert "Error creating command" in result.message


def test_update_custom_command_file_body(tmp_path):
    cmd_file = tmp_path / "my_cmd.md"
    cmd_file.write_text(
        "---\nname: my_cmd\ncategory: General\ntype: command\ndate: 2026-01-01\n---\n\necho hello"
    )

    result = update_custom_command_file(
        local_path=str(cmd_file),
        name="my_cmd",
        body="echo updated",
    )
    assert result.ok
    assert result.path == cmd_file
    content = cmd_file.read_text()
    assert "echo updated" in content
    assert "name: my_cmd" in content


def test_update_custom_command_file_rename(tmp_path):
    cmd_file = tmp_path / "old_name.md"
    cmd_file.write_text(
        "---\nname: old_name\ncategory: General\ntype: command\ndate: 2026-01-01\n---\n\necho hello"
    )

    result = update_custom_command_file(
        local_path=str(cmd_file),
        name="new_name",
        body="echo hello",
    )
    assert result.ok
    assert result.path.name == "new_name.md"
    assert result.path.exists()
    assert not cmd_file.exists()
    content = result.path.read_text()
    assert "name: new_name" in content
    assert "echo hello" in content


def test_update_custom_command_file_not_found(tmp_path):
    result = update_custom_command_file(
        local_path=str(tmp_path / "nonexistent.md"),
        name="test",
        body="body",
    )
    assert not result.ok
    assert "not found" in result.message


def test_update_custom_command_file_rename_conflict(tmp_path):
    (tmp_path / "keep.md").write_text(
        "---\nname: keep\ncategory: General\ntype: command\ndate: 2026-01-01\n---\n\nkeep"
    )
    conflict = tmp_path / "existing.md"
    conflict.write_text(
        "---\nname: existing\ncategory: General\ntype: command\ndate: 2026-01-01\n---\n\nexisting"
    )

    result = update_custom_command_file(
        local_path=str(tmp_path / "keep.md"),
        name="existing",
        body="updated",
    )
    assert not result.ok
    assert "already exists" in result.message


def test_update_custom_command_file_preserves_category(tmp_path):
    cmd_file = tmp_path / "cmd.md"
    cmd_file.write_text(
        "---\nname: cmd\ncategory: DevOps\ntype: command\ndate: 2026-01-01\n---\n\noriginal"
    )

    result = update_custom_command_file(
        local_path=str(cmd_file),
        name="cmd",
        body="updated body",
    )
    assert result.ok
    content = cmd_file.read_text()
    assert "category: DevOps" in content
    assert "updated body" in content
