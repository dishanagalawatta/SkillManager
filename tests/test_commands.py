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
    assert result.path is not None
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
    assert result.path is not None
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


def test_update_custom_command_file_changes_category(tmp_path):
    cmd_file = tmp_path / "cmd.md"
    cmd_file.write_text(
        "---\nname: cmd\ncategory: DevOps\ntype: command\ndate: 2026-01-01\n---\n\noriginal"
    )

    result = update_custom_command_file(
        local_path=str(cmd_file),
        name="cmd",
        body="updated body",
        category="NewCat",
    )
    assert result.ok
    content = cmd_file.read_text()
    assert "category: NewCat" in content
    assert "updated body" in content


def test_update_custom_command_file_preserves_existing_when_category_empty(tmp_path):
    cmd_file = tmp_path / "cmd.md"
    cmd_file.write_text(
        "---\nname: cmd\ncategory: DevOps\ntype: command\ndate: 2026-01-01\n---\n\noriginal"
    )

    result = update_custom_command_file(
        local_path=str(cmd_file),
        name="cmd",
        body="updated body",
        category="",
    )
    assert result.ok
    content = cmd_file.read_text()
    assert "category: DevOps" in content


def test_update_custom_command_file_moves_to_new_project(tmp_path):
    from skill_manager.core.quick_copy import project_label

    proj_a = tmp_path / "projA"
    proj_b = tmp_path / "projB"
    (proj_a / ".agents" / "skills").mkdir(parents=True)
    (proj_a / ".agents" / "commands").mkdir(parents=True)
    (proj_b / ".agents" / "skills").mkdir(parents=True)
    (proj_b / ".agents" / "commands").mkdir(parents=True)

    src = proj_a / ".agents" / "commands" / "cmd.md"
    src.write_text("---\nname: cmd\ncategory: DevOps\ntype: command\ndate: 2026-01-01\n---\n\nbody")

    result = update_custom_command_file(
        local_path=str(src),
        name="cmd",
        body="new body",
        category="NewCat",
        project_label_name=project_label(proj_b),
        project_paths=[str(proj_a), str(proj_b)],
    )
    assert result.ok
    assert not src.exists()
    dst = proj_b / ".agents" / "commands" / "cmd.md"
    assert dst.exists()
    assert "new body" in dst.read_text()
    assert "category: NewCat" in dst.read_text()


def test_update_custom_command_file_returns_conflict_marker(tmp_path):
    from skill_manager.core.quick_copy import project_label

    proj_a = tmp_path / "projA"
    proj_b = tmp_path / "projB"
    (proj_a / ".agents" / "skills").mkdir(parents=True)
    (proj_a / ".agents" / "commands").mkdir(parents=True)
    (proj_b / ".agents" / "skills").mkdir(parents=True)
    (proj_b / ".agents" / "commands").mkdir(parents=True)

    src = proj_a / ".agents" / "commands" / "cmd.md"
    src.write_text("---\nname: cmd\ncategory: X\ntype: command\ndate: 2026-01-01\n---\n\nbody")
    blocker = proj_b / ".agents" / "commands" / "cmd.md"
    blocker.write_text(
        "---\nname: cmd\ncategory: Y\ntype: command\ndate: 2026-01-01\n---\n\nexisting"
    )

    result = update_custom_command_file(
        local_path=str(src),
        name="cmd",
        body="new body",
        project_label_name=project_label(proj_b),
        project_paths=[str(proj_a), str(proj_b)],
    )
    assert not result.ok
    assert result.needs_conflict_resolution
    assert str(result.conflicting_path) == str(blocker)
    assert result.suggested_rename == "cmd-1.md"
    assert src.exists()


def test_update_custom_command_file_auto_renames_on_conflict(tmp_path):
    from skill_manager.core.quick_copy import project_label

    proj_a = tmp_path / "projA"
    proj_b = tmp_path / "projB"
    (proj_a / ".agents" / "skills").mkdir(parents=True)
    (proj_a / ".agents" / "commands").mkdir(parents=True)
    (proj_b / ".agents" / "skills").mkdir(parents=True)
    (proj_b / ".agents" / "commands").mkdir(parents=True)

    src = proj_a / ".agents" / "commands" / "cmd.md"
    src.write_text("---\nname: cmd\ntype: command\ndate: 2026-01-01\n---\n\nbody")
    blocker = proj_b / ".agents" / "commands" / "cmd.md"
    blocker.write_text("---\nname: cmd\ntype: command\ndate: 2026-01-01\n---\n\nexisting")

    result = update_custom_command_file(
        local_path=str(src),
        name="cmd",
        body="new body",
        project_label_name=project_label(proj_b),
        project_paths=[str(proj_a), str(proj_b)],
        on_conflict="rename",
    )
    assert result.ok
    assert not src.exists()
    assert blocker.exists()
    assert (proj_b / ".agents" / "commands" / "cmd-1.md").exists()


def test_update_custom_command_file_overwrites_on_conflict(tmp_path):
    from skill_manager.core.quick_copy import project_label

    proj_a = tmp_path / "projA"
    proj_b = tmp_path / "projB"
    (proj_a / ".agents" / "skills").mkdir(parents=True)
    (proj_a / ".agents" / "commands").mkdir(parents=True)
    (proj_b / ".agents" / "skills").mkdir(parents=True)
    (proj_b / ".agents" / "commands").mkdir(parents=True)

    src = proj_a / ".agents" / "commands" / "cmd.md"
    src.write_text("---\nname: cmd\ntype: command\ndate: 2026-01-01\n---\n\nbody")
    blocker = proj_b / ".agents" / "commands" / "cmd.md"
    blocker.write_text("---\nname: cmd\ntype: command\ndate: 2026-01-01\n---\n\nexisting")

    result = update_custom_command_file(
        local_path=str(src),
        name="cmd",
        body="new body",
        project_label_name=project_label(proj_b),
        project_paths=[str(proj_a), str(proj_b)],
        on_conflict="overwrite",
    )
    assert result.ok
    assert not src.exists()
    assert "new body" in blocker.read_text()


def test_update_custom_command_file_cancels_on_conflict(tmp_path):
    from skill_manager.core.quick_copy import project_label

    proj_a = tmp_path / "projA"
    proj_b = tmp_path / "projB"
    for p in (proj_a, proj_b):
        (p / ".agents" / "skills").mkdir(parents=True)
        (p / ".agents" / "commands").mkdir(parents=True)

    src = proj_a / ".agents" / "commands" / "cmd.md"
    src.write_text("---\nname: cmd\ntype: command\ndate: 2026-01-01\n---\n\noriginal")
    original_content = src.read_text()

    blocker = proj_b / ".agents" / "commands" / "cmd.md"
    blocker.write_text("---\nname: cmd\ntype: command\ndate: 2026-01-01\n---\n\nexisting")

    result = update_custom_command_file(
        local_path=str(src),
        name="cmd",
        body="new body",
        project_label_name=project_label(proj_b),
        project_paths=[str(proj_a), str(proj_b)],
        on_conflict="cancel",
    )
    assert not result.ok
    assert result.path == src
    assert src.exists()
    assert src.read_text() == original_content
    assert "existing" in blocker.read_text()
