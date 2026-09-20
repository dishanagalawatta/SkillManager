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
    ops = OpsController(app_mock)
    return ops, skill_obj


def test_update_multi_project_emits_single_batch(tmp_path: Path, qtbot):
    proj_a = tmp_path / "projA"
    proj_b = tmp_path / "projB"
    proj_c = tmp_path / "projC"
    for p in (proj_a, proj_b, proj_c):
        p.mkdir(parents=True)
    ops, _ = _make_ops(tmp_path, [proj_a, proj_b, proj_c], with_skill_in={"projA"})

    label_a = project_label(proj_a)
    cmd_path = ops.createCustomCommand(
        name="shared-cmd", body="Initial body", project_labels=[label_a], category="General"
    )
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
        project_labels=[project_label(p) for p in (proj_a, proj_b, proj_c)],
    )
    qtbot.wait(150)

    # Only ONE prompt total; batch path used for >1 project missing.
    assert len(singles) == 0, f"expected no single prompts, got {singles}"
    assert len(batches) == 1, f"expected one batch prompt, got {len(batches)}"
    batch = json.loads(batches[0])
    assert len(batch) == 2
    paths = {e["project_path"] for e in batch}
    assert paths == {str(proj_b), str(proj_c)}


def test_batch_confirm_copies_to_all_then_idempotent(tmp_path: Path, qtbot):
    proj_a = tmp_path / "projA"
    proj_b = tmp_path / "projB"
    for p in (proj_a, proj_b):
        p.mkdir(parents=True)
    ops, skill_obj = _make_ops(tmp_path, [proj_a, proj_b], with_skill_in=set())

    label_a = project_label(proj_a)
    label_b = project_label(proj_b)
    cmd_path = ops.createCustomCommand(
        name="shared-cmd", body="Initial body", project_labels=[label_a], category="General"
    )
    qtbot.wait(50)

    batches: list = []
    ops.commandSkillsCarryBatchPrompt.connect(lambda b: batches.append(b))
    singles: list = []
    ops.commandSkillsCarryPrompt.connect(lambda c, p, m: singles.append((c, p, m)))

    ops.updateCustomCommandFull(
        local_path=cmd_path,
        name="shared-cmd",
        body="Body with /multi-helper",
        category="General",
        project_labels=[label_a, label_b],
    )
    qtbot.wait(150)
    combined = batches + singles
    assert len(combined) >= 1
    payload = batches[0] if batches else None
    if payload is not None:
        batch = json.loads(payload)
        union = batch[0]["missing_skills"]
        ops.confirmCommandSkillsCarryBatch(payload, json.dumps(union))
        qtbot.wait(300)
        assert (proj_a / ".agents" / "skills" / "multi-helper").is_dir()
        assert (proj_b / ".agents" / "skills" / "multi-helper").is_dir()

        # Second identical update must be silent (idempotent).
        batches.clear()
        singles.clear()
        cmd_b = proj_b / ".agents" / "commands" / "shared-cmd.md"
        ops.updateCustomCommandFull(
            local_path=str(cmd_b) if cmd_b.exists() else cmd_path,
            name="shared-cmd",
            body="Body with /multi-helper",
            category="General",
            project_labels=[label_a, label_b],
        )
        qtbot.wait(150)
        assert batches == [] and singles == []
