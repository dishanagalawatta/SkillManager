from datetime import date

from skill_manager.core.commands import (
    build_command_content,
    build_command_filename,
    create_custom_command_file,
    create_custom_command_files_multi,
    find_command_holder_projects,
    update_custom_command_file,
    update_custom_command_file_multi,
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


def test_update_custom_command_file_skips_conflict_when_content_matches(tmp_path):
    """When the destination file has identical content, no conflict is raised."""
    from skill_manager.core.quick_copy import project_label

    proj_a = tmp_path / "projA"
    proj_b = tmp_path / "projB"
    (proj_a / ".agents" / "skills").mkdir(parents=True)
    (proj_a / ".agents" / "commands").mkdir(parents=True)
    (proj_b / ".agents" / "skills").mkdir(parents=True)
    (proj_b / ".agents" / "commands").mkdir(parents=True)

    src = proj_a / ".agents" / "commands" / "cmd.md"
    src.write_text("---\nname: cmd\ncategory: X\ntype: command\ndate: 2026-01-01\n---\n\nbody")

    # Blocker has the SAME content that update would produce
    expected_content = build_command_content("cmd", "body", "X")
    blocker = proj_b / ".agents" / "commands" / "cmd.md"
    blocker.write_text(expected_content)
    blocker_mtime = blocker.stat().st_mtime

    result = update_custom_command_file(
        local_path=str(src),
        name="cmd",
        body="body",
        category="X",
        project_label_name=project_label(proj_b),
        project_paths=[str(proj_a), str(proj_b)],
    )
    assert result.ok
    assert not result.needs_conflict_resolution
    assert result.path == blocker
    # File should not have been rewritten
    assert blocker.stat().st_mtime == blocker_mtime
    assert blocker.read_text() == expected_content


def test_update_custom_command_file_keeps_source_on_content_match(tmp_path):
    """When content matches, the source file should not be deleted."""
    from skill_manager.core.quick_copy import project_label

    proj_a = tmp_path / "projA"
    proj_b = tmp_path / "projB"
    (proj_a / ".agents" / "skills").mkdir(parents=True)
    (proj_a / ".agents" / "commands").mkdir(parents=True)
    (proj_b / ".agents" / "skills").mkdir(parents=True)
    (proj_b / ".agents" / "commands").mkdir(parents=True)

    src = proj_a / ".agents" / "commands" / "cmd.md"
    expected_content = build_command_content("cmd", "hello", "Cat")
    src.write_text(expected_content)

    blocker = proj_b / ".agents" / "commands" / "cmd.md"
    blocker.write_text(expected_content)

    result = update_custom_command_file(
        local_path=str(src),
        name="cmd",
        body="hello",
        category="Cat",
        project_label_name=project_label(proj_b),
        project_paths=[str(proj_a), str(proj_b)],
    )
    assert result.ok
    assert src.exists()
    assert blocker.read_text() == expected_content


def test_update_custom_command_file_still_conflicts_on_content_mismatch(tmp_path):
    """Regression: files with different content must still trigger conflict."""
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


def test_create_custom_command_files_multi_single_project(tmp_path):
    project_root = tmp_path / "proj1"
    (project_root / ".agents" / "skills").mkdir(parents=True)

    results = create_custom_command_files_multi(
        name="Start",
        body="echo 'hello'",
        project_labels=["proj1"],
        category="General",
        project_paths=[str(project_root / ".agents" / "skills")],
        created_on=date(2026, 6, 23),
    )
    assert len(results) == 1
    assert results[0].ok
    assert results[0].path is not None
    assert results[0].path.name == "Start.md"
    assert results[0].path.exists()


def test_create_custom_command_files_multi_two_projects(tmp_path):
    proj1 = tmp_path / "proj1"
    proj2 = tmp_path / "proj2"
    (proj1 / ".agents" / "skills").mkdir(parents=True)
    (proj2 / ".agents" / "skills").mkdir(parents=True)

    results = create_custom_command_files_multi(
        name="Deploy",
        body="deploy all",
        project_labels=["proj1", "proj2"],
        category="DevOps",
        project_paths=[str(proj1 / ".agents" / "skills"), str(proj2 / ".agents" / "skills")],
        created_on=date(2026, 6, 23),
    )
    assert len(results) == 2
    assert all(r.ok for r in results)
    assert (proj1 / ".agents" / "commands" / "Deploy.md").exists()
    assert (proj2 / ".agents" / "commands" / "Deploy.md").exists()


def test_create_custom_command_files_multi_empty_labels(tmp_path):
    results = create_custom_command_files_multi(
        name="Cmd",
        body="body",
        project_labels=[],
        category="cat",
        project_paths=[str(tmp_path)],
    )
    assert results == []


def test_create_custom_command_files_multi_duplicate_in_one(tmp_path):
    proj1 = tmp_path / "proj1"
    (proj1 / ".agents" / "skills").mkdir(parents=True)
    (proj1 / ".agents" / "commands").mkdir(parents=True)
    (proj1 / ".agents" / "commands" / "Cmd.md").write_text("existing")

    results = create_custom_command_files_multi(
        name="Cmd",
        body="new body",
        project_labels=["proj1"],
        category="cat",
        project_paths=[str(proj1 / ".agents" / "skills")],
    )
    assert len(results) == 1
    assert not results[0].ok
    assert "already exists" in results[0].message


def test_update_custom_command_file_multi_copies_to_all(tmp_path):
    from skill_manager.core.quick_copy import project_label

    proj1 = tmp_path / "proj1"
    proj2 = tmp_path / "proj2"
    (proj1 / ".agents" / "skills").mkdir(parents=True)
    (proj1 / ".agents" / "commands").mkdir(parents=True)
    (proj2 / ".agents" / "skills").mkdir(parents=True)

    src = proj1 / ".agents" / "commands" / "cmd.md"
    src.write_text(
        "---\nname: cmd\ncategory: DevOps\ntype: command\ndate: 2026-01-01\n---\n\noriginal"
    )

    results = update_custom_command_file_multi(
        local_path=str(src),
        name="cmd",
        body="updated",
        category="DevOps",
        project_labels=[project_label(proj1), project_label(proj2)],
        project_paths=[str(proj1), str(proj2)],
    )
    assert len(results) == 2
    assert results[0].ok  # canonical
    assert results[1].ok  # fan-out
    assert "updated" in (proj2 / ".agents" / "commands" / "cmd.md").read_text()


def test_update_custom_command_file_multi_first_label_is_canonical(tmp_path):
    from skill_manager.core.quick_copy import project_label

    proj1 = tmp_path / "proj1"
    proj2 = tmp_path / "proj2"
    (proj1 / ".agents" / "skills").mkdir(parents=True)
    (proj1 / ".agents" / "commands").mkdir(parents=True)
    (proj2 / ".agents" / "skills").mkdir(parents=True)

    src = proj1 / ".agents" / "commands" / "cmd.md"
    src.write_text("---\nname: cmd\ncategory: X\ntype: command\ndate: 2026-01-01\n---\n\nbody")

    results = update_custom_command_file_multi(
        local_path=str(src),
        name="cmd",
        body="new",
        category="X",
        project_labels=[project_label(proj1), project_label(proj2)],
        project_paths=[str(proj1), str(proj2)],
    )
    assert results[0].ok
    assert results[0].path == proj1 / ".agents" / "commands" / "cmd.md"
    assert src.exists()


def test_update_custom_command_file_multi_partial_conflict(tmp_path):
    from skill_manager.core.quick_copy import project_label

    proj1 = tmp_path / "proj1"
    proj2 = tmp_path / "proj2"
    proj3 = tmp_path / "proj3"
    (proj1 / ".agents" / "skills").mkdir(parents=True)
    (proj1 / ".agents" / "commands").mkdir(parents=True)
    (proj2 / ".agents" / "skills").mkdir(parents=True)
    (proj2 / ".agents" / "commands").mkdir(parents=True)
    (proj3 / ".agents" / "skills").mkdir(parents=True)
    (proj3 / ".agents" / "commands").mkdir(parents=True)

    src = proj1 / ".agents" / "commands" / "cmd.md"
    src.write_text("---\nname: cmd\ncategory: X\ntype: command\ndate: 2026-01-01\n---\n\nbody")

    # Command exists in proj1 and proj2 (holders), proj3 is new
    # Conflict only on proj3
    (proj3 / ".agents" / "commands" / "cmd.md").write_text("existing")

    results = update_custom_command_file_multi(
        local_path=str(src),
        name="cmd",
        body="updated",
        category="X",
        project_labels=[project_label(proj1), project_label(proj2), project_label(proj3)],
        project_paths=[str(proj1), str(proj2), str(proj3)],
    )
    # Canonical (proj1, from keep_set) succeeds
    assert results[0].ok
    # Fan-out to proj3 (add_set) — may conflict or overwrite depending on on_conflict
    # proj2 is in keep_set, so no fan-out to it


def test_find_command_holder_projects(tmp_path):
    proj1 = tmp_path / "proj1"
    proj2 = tmp_path / "proj2"
    (proj1 / ".agents" / "skills").mkdir(parents=True)
    (proj1 / ".agents" / "commands").mkdir(parents=True)
    (proj1 / ".agents" / "commands" / "Test.md").write_text("x")
    (proj2 / ".agents" / "skills").mkdir(parents=True)
    (proj2 / ".agents" / "commands").mkdir(parents=True)
    (proj2 / ".agents" / "commands" / "Test.md").write_text("y")

    holders = find_command_holder_projects(
        "Test",
        [str(proj1 / ".agents" / "skills"), str(proj2 / ".agents" / "skills")],
    )
    assert len(holders) == 2
    assert "proj1" in holders
    assert "proj2" in holders


def test_find_command_holder_projects_no_match(tmp_path):
    proj1 = tmp_path / "proj1"
    (proj1 / ".agents" / "skills").mkdir(parents=True)
    (proj1 / ".agents" / "commands").mkdir(parents=True)
    (proj1 / ".agents" / "commands" / "Other.md").write_text("x")

    holders = find_command_holder_projects(
        "Test",
        [str(proj1 / ".agents" / "skills")],
    )
    assert holders == []
