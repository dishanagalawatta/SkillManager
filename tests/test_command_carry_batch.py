"""Batch carry regression: multi-project update emits ONE prompt and is idempotent."""

import json
from pathlib import Path
from unittest.mock import MagicMock

from skill_manager.core.models.entities import Skill
from skill_manager.core.quick_copy import project_label


def _make_ops(tmp_path: Path, projects: list[Path], with_skill_in: set[str] | None = None):
    from skill_manager.controllers.ops_controller import OpsController

    with_skill_in = with_skill_in or set()
    app_mock = MagicMock()
    app_mock._projects = [str(p) for p in projects]
    source_dir = tmp_path / "sources" / "global"
    source_dir.mkdir(parents=True, exist_ok=True)
    app_mock._sources = [str(source_dir)]
    app_mock._archive_paths = []
    app_mock._starred_paths = []
    app_mock._project_aliases = {}

    skill_folder_global = source_dir / "multi-helper"
    skill_folder_global.mkdir(exist_ok=True)
    (skill_folder_global / "SKILL.md").write_text("# Multi Helper Skill\n")
    for proj in projects:
        if proj.name in with_skill_in:
            dest = proj / ".agents" / "skills" / "multi-helper"
            dest.mkdir(parents=True, exist_ok=True)
            (dest / "SKILL.md").write_text("# Multi Helper\n")

    skill_obj = Skill(
        name="multi-helper",
        folder_name="multi-helper",
        local_path=str(skill_folder_global),
    )
    app_mock._library_model._all_skills = [skill_obj]
    app_mock._selected_skill = skill_obj
    app_mock._quick_copy_model = MagicMock()
    app_mock.task_runner.run.side_effect = lambda fn: fn()
    # The Library's active project owns the canonical command file.
    app_mock._current_project_label = project_label(projects[0])
    ops = OpsController(app_mock)
    return ops, skill_obj


def test_update_emits_single_carry_prompt_for_owning_project(tmp_path: Path, qtbot):
    """Editing a command prompts once, for the project that owns it.

    The dialog no longer fans a command out to several projects, so the
    carry check runs against the owning project only: exactly one prompt,
    never a batch.
    """
    proj_a = tmp_path / "projA"
    proj_b = tmp_path / "projB"
    proj_c = tmp_path / "projC"
    for p in (proj_a, proj_b, proj_c):
        p.mkdir(parents=True)
    ops, _ = _make_ops(tmp_path, [proj_a, proj_b, proj_c], with_skill_in={"projA"})

    # The command lives in projB, which does NOT have the helper skill.
    ops.app._current_project_label = project_label(proj_b)
    cmd_path = ops.createCustomCommand(name="shared-cmd", body="Initial body", category="General")
    qtbot.wait(50)

    singles: list = []
    batches: list = []
    ops.commandSkillsCarryPrompt.connect(lambda c, p, m: singles.append((c, p, m)))
    ops.commandSkillsCarryBatchPrompt.connect(lambda b: batches.append(b))

    ops.updateCustomCommandFull(
        local_path=cmd_path,
        name="shared-cmd",
        body="Updated body referencing /multi-helper",
        category="General",
    )
    qtbot.waitUntil(lambda: len(singles) >= 1, timeout=5000)

    # Only ONE prompt total, and it is a single-project prompt.
    assert len(batches) == 0, f"expected no batch prompts, got {batches}"
    assert len(singles) == 1, f"expected one prompt, got {len(singles)}"
    cmd_json, proj_str, miss_json = singles[0]
    assert json.loads(cmd_json) == [str(cmd_path)]
    assert Path(proj_str) == proj_b
    assert json.loads(miss_json)[0]["name"] == "multi-helper"


def test_carry_prompt_is_idempotent_after_confirming(tmp_path: Path, qtbot):
    """Once the skill is carried, an identical edit must not prompt again."""
    proj_a = tmp_path / "projA"
    proj_b = tmp_path / "projB"
    for p in (proj_a, proj_b):
        p.mkdir(parents=True)
    ops, _ = _make_ops(tmp_path, [proj_a, proj_b], with_skill_in=set())

    ops.app._current_project_label = project_label(proj_b)
    cmd_path = ops.createCustomCommand(name="shared-cmd", body="Initial body", category="General")
    qtbot.wait(50)

    singles: list = []
    batches: list = []
    ops.commandSkillsCarryPrompt.connect(lambda c, p, m: singles.append((c, p, m)))
    ops.commandSkillsCarryBatchPrompt.connect(lambda b: batches.append(b))

    ops.updateCustomCommandFull(
        local_path=cmd_path,
        name="shared-cmd",
        body="Body with /multi-helper",
        category="General",
    )
    qtbot.waitUntil(lambda: len(singles) >= 1, timeout=5000)

    _cmd_json, _proj_str, miss_json = singles[0]
    missing = json.loads(miss_json)
    ops.confirmCommandSkillsCarry(str(proj_b), json.dumps([str(cmd_path)]), json.dumps(missing))
    qtbot.wait(300)
    assert (proj_b / ".agents" / "skills" / "multi-helper").is_dir()

    # Second identical update must be silent (idempotent).
    singles.clear()
    batches.clear()
    ops.updateCustomCommandFull(
        local_path=cmd_path,
        name="shared-cmd",
        body="Body with /multi-helper",
        category="General",
    )
    qtbot.wait(150)
    assert batches == [] and singles == []
