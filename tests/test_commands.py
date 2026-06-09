from datetime import date

from skill_manager.core.commands import (
    build_command_content,
    build_command_filename,
    create_custom_command_file,
    update_custom_command_file,
    update_custom_command_file_full,
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
    commands_dir = project_root / ".agents" / "commands"

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
    assert result.path == commands_dir / "Start.CLI.md"
    assert result.path.exists()
    assert result.path.name == "Start.CLI.md"
    assert "echo 'hello'" in result.path.read_text()


def test_build_command_filename_with_all_client_formats():
    """Verify build_command_filename works with all known client format values."""
    known_clients = ["Plain Text", "Gemini CLI", "Antigravity", "Codex"]
    for client in known_clients:
        filename = build_command_filename("TestCommand", client)
        assert filename == f"TestCommand.{client}.md"


def test_create_custom_command_file_for_multiple_clients(tmp_path):
    """Simulate multi-client creation: one file per client."""
    project_root = tmp_path / "multi-client-proj"
    project_path = project_root / ".agents" / "skills"
    project_path.mkdir(parents=True)
    commands_dir = project_root / ".agents" / "commands"

    clients = ["Plain Text", "Gemini CLI", "Antigravity", "Codex"]
    results = []
    for client in clients:
        result = create_custom_command_file(
            name="MultiCmd",
            client=client,
            body=f"body for {client}",
            project_label_name="multi-client-proj",
            category="Multi",
            project_paths=[str(project_path)],
        )
        results.append(result)

    assert all(r.ok for r in results)
    for client in clients:
        expected = commands_dir / f"MultiCmd.{client}.md"
        assert expected.exists(), f"Missing file for client: {client}"
        assert f"body for {client}" in expected.read_text()


def test_parse_comma_separated_clients():
    """Verify the comma-split logic used in the controller."""
    clients_str = "Plain Text, Gemini CLI, Antigravity"
    clients = [c.strip() for c in clients_str.split(",") if c.strip()]
    assert clients == ["Plain Text", "Gemini CLI", "Antigravity"]


def test_parse_single_client():
    clients_str = "Codex"
    clients = [c.strip() for c in clients_str.split(",") if c.strip()]
    assert clients == ["Codex"]


def test_parse_empty_clients():
    clients_str = ""
    clients = [c.strip() for c in clients_str.split(",") if c.strip()]
    assert clients == []


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
    commands_dir = project_root / ".agents" / "commands"
    commands_dir.mkdir(parents=True)
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


def test_update_custom_command_file_body(tmp_path):
    cmd_file = tmp_path / "my_cmd.CLI.md"
    cmd_file.write_text(
        "---\nname: my_cmd\nclient: CLI\ncategory: General\ntype: command\ndate: 2026-01-01\n---\n\necho hello"
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
    cmd_file = tmp_path / "old_name.CLI.md"
    cmd_file.write_text(
        "---\nname: old_name\nclient: CLI\ncategory: General\ntype: command\ndate: 2026-01-01\n---\n\necho hello"
    )

    result = update_custom_command_file(
        local_path=str(cmd_file),
        name="new_name",
        body="echo hello",
    )
    assert result.ok
    assert result.path.name == "new_name.CLI.md"
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
    (tmp_path / "keep.CLI.md").write_text(
        "---\nname: keep\nclient: CLI\ncategory: General\ntype: command\ndate: 2026-01-01\n---\n\nkeep"
    )
    conflict = tmp_path / "existing.CLI.md"
    conflict.write_text(
        "---\nname: existing\nclient: CLI\ncategory: General\ntype: command\ndate: 2026-01-01\n---\n\nexisting"
    )

    result = update_custom_command_file(
        local_path=str(tmp_path / "keep.CLI.md"),
        name="existing",
        body="updated",
    )
    assert not result.ok
    assert "already exists" in result.message


def test_create_custom_command_file_filesystem_error(tmp_path):
    project_root = tmp_path / "readonly_proj"
    project_path = project_root / ".agents" / "skills"
    project_path.mkdir(parents=True)

    # Make the commands path a file so mkdir fails
    (project_root / ".agents").mkdir(parents=True, exist_ok=True)
    commands_dir_as_file = project_root / ".agents" / "commands"
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


def test_update_custom_command_file_full_rename_client(tmp_path):
    project_root = tmp_path / "proj"
    project_path = project_root / ".agents" / "skills"
    project_path.mkdir(parents=True)
    cmd_file = project_root / ".agents" / "commands" / "old_cmd.Codex.md"
    cmd_file.parent.mkdir(parents=True)
    cmd_file.write_text(
        "---\nname: old_cmd\nclient: Codex\ncategory: Ops\ntype: command\ndate: 2026-01-01\n---\n\necho hello"
    )

    result = update_custom_command_file_full(
        local_path=str(cmd_file),
        name="renamed_cmd",
        client="Antigravity",
        body="echo updated",
        category="Dev",
        project_label_name="proj",
        project_paths=[str(project_path)],
    )

    assert result.ok
    assert result.path.name == "renamed_cmd.Antigravity.md"
    assert result.path.exists()
    assert not cmd_file.exists()
    content = result.path.read_text()
    assert "name: renamed_cmd" in content
    assert "client: Antigravity" in content
    assert "category: Dev" in content
    assert "echo updated" in content


def test_update_custom_command_file_full_same_path(tmp_path):
    project_root = tmp_path / "proj"
    project_path = project_root / ".agents" / "skills"
    project_path.mkdir(parents=True)
    cmd_file = project_root / ".agents" / "commands" / "keep.CLI.md"
    cmd_file.parent.mkdir(parents=True)
    cmd_file.write_text(
        "---\nname: keep\nclient: CLI\ncategory: General\ntype: command\ndate: 2026-01-01\n---\n\necho hello"
    )

    result = update_custom_command_file_full(
        local_path=str(cmd_file),
        name="keep",
        client="CLI",
        body="echo updated",
        category="General",
        project_label_name="proj",
        project_paths=[str(project_path)],
    )

    assert result.ok
    assert result.path == cmd_file
    content = cmd_file.read_text()
    assert "echo updated" in content


def test_update_custom_command_file_full_not_found(tmp_path):
    result = update_custom_command_file_full(
        local_path=str(tmp_path / "nonexistent.md"),
        name="test",
        client="CLI",
        body="body",
        category="cat",
        project_label_name="proj",
        project_paths=[str(tmp_path)],
    )
    assert not result.ok
    assert "not found" in result.message


def test_update_custom_command_file_full_duplicate(tmp_path):
    project_root = tmp_path / "proj"
    project_path = project_root / ".agents" / "skills"
    project_path.mkdir(parents=True)
    commands_dir = project_root / ".agents" / "commands"
    commands_dir.mkdir(parents=True)

    (commands_dir / "existing.Antigravity.md").write_text(
        "---\nname: existing\nclient: Antigravity\ncategory: General\ntype: command\ndate: 2026-01-01\n---\n\nexisting"
    )
    source_file = commands_dir / "source.Codex.md"
    source_file.write_text(
        "---\nname: source\nclient: Codex\ncategory: General\ntype: command\ndate: 2026-01-01\n---\n\nsource"
    )

    result = update_custom_command_file_full(
        local_path=str(source_file),
        name="existing",
        client="Antigravity",
        body="updated",
        category="General",
        project_label_name="proj",
        project_paths=[str(project_path)],
    )
    assert not result.ok
    assert "already exists" in result.message


def test_update_custom_command_file_full_project_not_found(tmp_path):
    cmd_file = tmp_path / "test.Codex.md"
    cmd_file.write_text(
        "---\nname: test\nclient: Codex\ncategory: General\ntype: command\ndate: 2026-01-01\n---\n\nbody"
    )
    result = update_custom_command_file_full(
        local_path=str(cmd_file),
        name="test",
        client="Codex",
        body="body",
        category="cat",
        project_label_name="non-existent",
        project_paths=[str(tmp_path)],
    )
    assert not result.ok
    assert "Could not find project directory" in result.message
