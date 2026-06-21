from skill_manager.core.updater import update_projects


def test_update_projects_success(temp_dir):
    # Setup sources
    source_dir = temp_dir / "sources"
    source_dir.mkdir()
    skill_a_v2 = source_dir / "skill-a"
    skill_a_v2.mkdir()
    (skill_a_v2 / "SKILL.md").write_text("v2 content")

    # Setup targets
    target_dir = temp_dir / "projects"
    target_dir.mkdir()
    project_skill_a = target_dir / "skill-a"
    project_skill_a.mkdir()
    (project_skill_a / "SKILL.md").write_text("v1 content")

    # Update
    result = update_projects([str(target_dir)], [str(source_dir)])
    assert result is not None
    updated, skipped = result

    assert updated == 1
    assert skipped == 0
    assert (project_skill_a / "SKILL.md").read_text() == "v2 content"


def test_update_projects_priority(temp_dir):
    source_1 = temp_dir / "source1"
    source_1.mkdir()
    (source_1 / "skill-a").mkdir()
    (source_1 / "skill-a" / "SKILL.md").write_text("source 1 content")

    source_2 = temp_dir / "source2"
    source_2.mkdir()
    (source_2 / "skill-a").mkdir()
    (source_2 / "skill-a" / "SKILL.md").write_text("source 2 content")

    target_dir = temp_dir / "target"
    target_dir.mkdir()
    (target_dir / "skill-a").mkdir()

    # Priority: source1 > source2
    update_projects([str(target_dir)], [str(source_1), str(source_2)])
    assert (target_dir / "skill-a" / "SKILL.md").read_text() == "source 1 content"

    # Priority: source2 > source1
    update_projects([str(target_dir)], [str(source_2), str(source_1)])
    assert (target_dir / "skill-a" / "SKILL.md").read_text() == "source 2 content"


def test_update_projects_skip(temp_dir):
    source_dir = temp_dir / "source"
    source_dir.mkdir()

    target_dir = temp_dir / "target"
    target_dir.mkdir()
    (target_dir / "unknown-skill").mkdir()

    result = update_projects([str(target_dir)], [str(source_dir)])
    assert result is not None
    updated, skipped = result
    assert updated == 0
    assert skipped == 1
