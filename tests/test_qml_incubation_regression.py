"""Regression test — _end_batch uses beginResetModel for first population.

When _begin_batch/_end_batch wraps setSkills on an empty model, _end_batch
must emit beginResetModel/endResetModel (not layoutAboutToBeChanged/layoutChanged).
This avoids the 'Object or context destroyed during incubation' QML warning
that occurs when layoutChanged fires while QML delegates are incubating.

Two tests:

1. end_batch_from_empty — verifies _end_batch fires beginResetModel/endResetModel
   when the model was empty before the batch.

2. end_batch_from_populated — verifies _end_batch fires layoutChanged
   when the model was already populated (existing optimization preserved).

Run with::

    uv run pytest tests/test_qml_incubation_regression.py -v
"""

from __future__ import annotations

import pytest


def _make_skill(i: int) -> dict[str, object]:
    """Build a minimal skill dict matching core/schemas.py shape."""
    return {
        "local_path": f"/test/skill_{i}",
        "name": f"Skill {i}",
        "body_content": f"Body {i}",
        "category": "Test",
        "type": "skill",
        "main_category_name": "Test",
        "sub_category_name": "",
        "is_bookmarked": False,
        "is_archived": False,
        "is_command": False,
        "is_package": False,
        "project": "TestProject",
    }


@pytest.fixture
def model(qapp, mock_config, temp_dir):
    """Fresh SkillModel for each test."""
    from skill_manager.core.models.qt_model import SkillModel

    return SkillModel(config=mock_config)


class TestEndBatchFirstPopulation:
    """_end_batch must use beginResetModel when transitioning from empty."""

    def test_end_batch_from_empty_emits_reset(self, model, qapp):
        """_end_batch on empty model fires modelReset (beginResetModel/endResetModel)."""
        reset_signals: list[str] = []
        model.modelReset.connect(lambda: reset_signals.append("reset"))
        layout_signals: list[str] = []
        model.layoutAboutToBeChanged.connect(lambda: layout_signals.append("about"))
        model.layoutChanged.connect(lambda: layout_signals.append("changed"))

        # Verify model is empty
        assert model.rowCount() == 0

        # Simulate discovery_controller cache load path
        skills = [_make_skill(i) for i in range(50)]
        model._begin_batch()
        model.setSkills(skills)  # suppressed by batch
        model._end_batch()  # must fire beginResetModel/endResetModel

        # _end_batch uses beginResetModel/endResetModel when was_empty=True
        assert "reset" in reset_signals, (
            "modelReset was not emitted during _end_batch from empty model"
        )
        # layoutAboutToBeChanged should NOT be emitted when reset=True
        assert "about" not in layout_signals, (
            "layoutAboutToBeChanged was emitted during _end_batch from empty model "
            "(should use beginResetModel instead)"
        )

    def test_end_batch_from_populated_uses_diff(self, model, qapp):
        """_end_batch on populated model uses diff (no layoutChanged)."""
        reset_signals: list[str] = []
        model.modelReset.connect(lambda: reset_signals.append("reset"))
        layout_signals: list[str] = []
        model.layoutAboutToBeChanged.connect(lambda: layout_signals.append("about"))
        model.layoutChanged.connect(lambda: layout_signals.append("changed"))
        insert_signals: list[str] = []
        model.rowsInserted.connect(lambda *args: insert_signals.append("insert"))

        # Pre-populate model
        model.setSkills([_make_skill(i) for i in range(20)])
        reset_signals.clear()
        layout_signals.clear()

        # Simulate config_controller batch (multiple filter changes)
        skills = [_make_skill(i) for i in range(30)]
        model._begin_batch()
        model.setSkills(skills)  # suppressed by batch
        model._end_batch()       # should use diff (model was not empty)

        # Should NOT emit layout or reset signals — diff emits granular signals
        assert "about" not in layout_signals, (
            "layoutAboutToBeChanged was emitted during _end_batch from populated model "
            "(should use diff-based update)"
        )
        assert "reset" not in reset_signals, (
            "modelReset was emitted during _end_batch from populated model "
            "(should use diff-based update)"
        )
        # Should emit granular rowsInserted for the new skills
        assert "insert" in insert_signals, (
            "rowsInserted was not emitted during _end_batch from populated model"
        )

    def test_end_batch_empty_model_has_correct_row_count(self, model, qapp):
        """After _end_batch from empty, model has correct row count."""
        skills = [_make_skill(i) for i in range(100)]

        model._begin_batch()
        model.setSkills(skills)
        model._end_batch()

        assert model.rowCount() == 100

    def test_direct_set_skills_uses_reset(self, model, qapp):
        """Direct setSkills (no batch) on empty model uses beginResetModel."""
        reset_signals: list[str] = []
        model.modelReset.connect(lambda: reset_signals.append("reset"))

        assert model.rowCount() == 0

        skills = [_make_skill(i) for i in range(30)]
        model.setSkills(skills)

        assert "reset" in reset_signals
        assert model.rowCount() == 30

    def test_end_batch_add_or_update_skills_from_populated_uses_diff(self, model, qapp):
        """_end_batch after addOrUpdateSkills on populated model uses diff (no layoutChanged)."""
        layout_signals: list[str] = []
        model.layoutAboutToBeChanged.connect(lambda: layout_signals.append("about"))
        model.layoutChanged.connect(lambda: layout_signals.append("changed"))

        insert_signals: list[str] = []
        model.rowsInserted.connect(lambda *args: insert_signals.append("insert"))

        # Pre-populate model
        model.setSkills([_make_skill(i) for i in range(20)])
        layout_signals.clear()

        # Simulate incremental update
        skills = [_make_skill(i) for i in range(22)]  # 2 new skills
        model._begin_batch()
        model.addOrUpdateSkills(skills)
        model._end_batch()

        # Should NOT emit layout signals because it used diff
        assert "about" not in layout_signals
        assert "changed" not in layout_signals
        # Should emit granular rowsInserted instead
        assert "insert" in insert_signals
        assert model.rowCount() == 22
