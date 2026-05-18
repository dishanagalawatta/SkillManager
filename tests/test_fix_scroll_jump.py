"""
Purpose: Test the fix for the scroll jump issue in the SkillManager QML UI by validating the new `filterByClient` property on `SkillModel`.
Usage: uv run pytest tests/test_fix_scroll_jump.py
"""

from typing import Any

import pytest

from skill_manager.core.models import SkillModel


@pytest.fixture
def sample_skills() -> list[dict[str, Any]]:
    return [
        {
            "name": "Skill A",
            "category": "Dev",
            "local_path": "/a",
            "is_selected": False,
            "is_archived": False,
            "client": "Antigravity",
        },
        {
            "name": "Skill B",
            "category": "Core",
            "local_path": "/b",
            "is_selected": False,
            "is_archived": False,
            "client": "Codex",
        },
    ]


def test_default_filter_by_client_enabled(qapp: Any, sample_skills: list[dict[str, Any]]) -> None:
    """Verify that by default, filterByClient is True and client filtering behaves normally, triggering layout signals."""
    model = SkillModel()
    model.setSkills(sample_skills)

    assert model.filterByClient is True

    # Track layout changes
    layout_changed_called = False

    def on_layout_changed() -> None:
        nonlocal layout_changed_called
        layout_changed_called = True

    model.layoutChanged.connect(on_layout_changed)

    # Filtering to "Antigravity" should hide Codex (Skill B) and trigger layoutChanged signal
    model.clientFilter = "Antigravity"
    assert model.clientFilter == "Antigravity"
    assert model.rowCount() == 1
    assert model.data(model.index(0, 0), SkillModel.NameRole) == "Skill A"
    assert layout_changed_called is True


def test_filter_by_client_disabled(qapp: Any, sample_skills: list[dict[str, Any]]) -> None:
    """Verify that when filterByClient is set to False, clientFilter changes do not trigger layout signals or filter results."""
    model = SkillModel()
    model.setSkills(sample_skills)

    # Disable client-based filtering in the model
    model.filterByClient = False
    assert model.filterByClient is False

    # Track layout signals and model resets
    signal_emitted = False

    def on_signal() -> None:
        nonlocal signal_emitted
        signal_emitted = True

    model.layoutAboutToBeChanged.connect(on_signal)
    model.layoutChanged.connect(on_signal)
    model.modelAboutToBeReset.connect(on_signal)
    model.modelReset.connect(on_signal)

    # Changing clientFilter should NOT apply filtering or emit signals, but it should still update the property
    model.clientFilter = "Antigravity"
    assert model.clientFilter == "Antigravity"

    # Both skills should still be present because filtering is disabled
    assert model.rowCount() == 2
    assert signal_emitted is False
