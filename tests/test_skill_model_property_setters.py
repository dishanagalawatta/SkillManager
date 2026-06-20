"""Runtime assertion that every @Property setter on SkillModel fires.

The PySide6 6.11.0 stub types ``@Property`` results as opaque instances
of the ``Property`` class, so static type-checkers reject assignments
like ``model.showArchived = True``. We work around that in
``qt_model.pyi`` by re-declaring the writable properties as plain
instance attributes. This test guards the *runtime* side: if a future
refactor breaks a setter (e.g. someone drops the ``@propname.setter``
decorator), the corresponding ``*Changed`` signal must stop firing
and the underlying ``_state`` field must stop mutating. Both are
asserted here.

If this test starts failing, the typing stub and the runtime
implementation have drifted. Either restore the setter wiring in
``qt_model.py`` or update ``qt_model.pyi`` to match the new shape.
"""

from __future__ import annotations

import pytest
from PySide6.QtCore import Qt

from skill_manager.core.models import SkillModel


def _skill_list() -> list[dict]:
    return [
        {
            "name": "Skill A",
            "category": "Dev",
            "local_path": "/a",
            "is_selected": False,
            "is_archived": False,
        },
        {
            "name": "Skill B",
            "category": "Core",
            "local_path": "/b",
            "is_selected": False,
            "is_archived": False,
        },
    ]


def _capture(signal):
    """Return a list that the connected slot appends to on each emit."""
    bucket: list[None] = []
    signal.connect(lambda: bucket.append(None))
    return bucket


@pytest.fixture
def model(qapp):
    m = SkillModel()
    m.setSkills(_skill_list())
    return m


def test_filter_text_setter_emits_and_mutates(model: SkillModel) -> None:
    bucket = _capture(model.filterChanged)
    model.filterText = "hello"
    assert model._state.filter_text == "hello"
    assert len(bucket) == 1


def test_show_archived_setter_emits_and_mutates(model: SkillModel) -> None:
    bucket = _capture(model.showArchivedChanged)
    model.showArchived = True
    assert model._state.show_archived is True
    assert len(bucket) == 1


def test_category_filter_setter_emits_and_mutates(model: SkillModel) -> None:
    bucket = _capture(model.categoryFilterChanged)
    model.categoryFilter = "Dev"
    assert model._state.category_filter == "Dev"
    assert len(bucket) == 1


def test_collection_filter_setter_emits_and_mutates(model: SkillModel) -> None:
    bucket = _capture(model.collectionFilterChanged)
    model.collectionFilter = True
    assert model._state.collection_filter is True
    assert len(bucket) == 1


def test_project_filter_setter_emits_and_mutates(model: SkillModel) -> None:
    bucket = _capture(model.projectFilterChanged)
    model.projectFilter = "Project X"
    assert model._state.project_filter == "Project X"
    assert len(bucket) == 1


def test_client_filter_setter_emits_and_mutates(model: SkillModel) -> None:
    bucket = _capture(model.clientFilterChanged)
    model.clientFilter = "Codex"
    assert model._state.client_filter == "Codex"
    assert len(bucket) == 1


def test_filter_by_client_setter_emits_and_mutates(model: SkillModel) -> None:
    bucket = _capture(model.filterByClientChanged)
    model.filterByClient = True
    assert model._state.filter_by_client is True
    assert len(bucket) == 1


def test_show_commands_setter_emits_and_mutates(model: SkillModel) -> None:
    bucket = _capture(model.showCommandsChanged)
    model.showCommands = False
    assert model._state.show_commands is False
    assert len(bucket) == 1


def test_show_starred_setter_emits_and_mutates(model: SkillModel) -> None:
    bucket = _capture(model.showStarredChanged)
    model.showStarred = False
    assert model._state.show_starred is False
    assert len(bucket) == 1


@pytest.mark.parametrize(
    "value,expected",
    [
        (Qt.CheckState.Checked, True),
        (True, True),
        (Qt.CheckState.Unchecked, False),
        (False, False),
    ],
)
def test_is_package_only_setter_emits_and_mutates(model: SkillModel, value, expected) -> None:
    bucket = _capture(model.isPackageOnlyChanged)
    model.isPackageOnly = value
    assert model._state.is_package_only is expected
    assert len(bucket) == 1


def test_setters_dedupe_when_value_unchanged(model: SkillModel) -> None:
    """Setting the same value twice must only emit once.

    The runtime ``@prop.setter`` implementations guard against
    redundant emits with an ``if self._state.x != value`` check. A
    regression that removes the guard would emit on every assignment
    and cause downstream re-renders.
    """
    bucket = _capture(model.categoryFilterChanged)
    model.categoryFilter = "Dev"
    model.categoryFilter = "Dev"
    assert len(bucket) == 1
