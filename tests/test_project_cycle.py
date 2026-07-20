"""Tests for the top-bar project cycle feature (last/current swap).

Covers:
1. ``setCurrentProject`` records the previous project as ``lastProject``.
2. ``cycleProject`` toggles current and last back and forth.
3. ``cycleProject`` is a no-op when there is no previous project.
4. The last project is persisted and restored across controller instances.
"""

from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import pytest

from skill_manager.core.quick_copy import project_label


@contextmanager
def _patched_app():
    patches = [
        patch("skill_manager.app.ConfigManager"),
        patch("skill_manager.app.BackgroundTaskRunner"),
        patch("skill_manager.app.QtScheduler"),
        patch("skill_manager.app.load_archive", return_value=[]),
        patch("skill_manager.app.load_starred", return_value=[]),
        patch("skill_manager.app.get_diagnostic_logger"),
    ]
    for p in patches:
        p.start()
    try:
        yield
    finally:
        for p in patches:
            p.stop()


def _make_config(projects, aliases=None):
    cfg = MagicMock()
    data = {
        "sources": [],
        "projects": projects,
        "project_aliases": aliases or {},
        "default_client": "Last Selected",
        "client_format": "Antigravity",
        "skills": [],
        "custom_collections": {},
        "skill_package_auto_update_mode": "off",
        "collapsed_categories": [],
        "show_archived": False,
        "category_filter": "",
        "collection_filter": False,
        "project_filter": "",
        "show_commands": True,
        "show_starred": True,
        "is_package_only": None,
        "project_selections": {},
        "last_project_label": "",
    }

    # Link set()/get() so the mock persists like ConfigManager (writes to disk).
    def _set(key, value):
        data[key] = value

    cfg.get = MagicMock(side_effect=lambda key, default=None: data.get(key, default))
    cfg.set = MagicMock(side_effect=_set)
    return cfg


def _make_controller(projects, config):
    from skill_manager.app import AppController

    return AppController(skip_initial_load=True, config=config)


@pytest.fixture
def app_env():
    with _patched_app():
        yield


def test_set_current_project_records_last(app_env):
    projects = ["/work/p1/.agents/skills", "/work/p2/.agents/skills"]
    ctrl = _make_controller(projects, _make_config(projects))
    l1 = project_label(projects[0])
    l2 = project_label(projects[1])

    # Starts on the first project with no previous project yet.
    assert ctrl.currentProject == l1
    assert ctrl.lastProject == ""

    ctrl.setCurrentProject(l2)
    assert ctrl.currentProject == l2
    assert ctrl.lastProject == l1


def test_cycle_project_swaps_current_and_last(app_env):
    projects = ["/work/p1/.agents/skills", "/work/p2/.agents/skills"]
    ctrl = _make_controller(projects, _make_config(projects))
    l1 = project_label(projects[0])
    l2 = project_label(projects[1])

    ctrl.setCurrentProject(l2)  # current=l2, last=l1
    ctrl.cycleProject()  # current=l1, last=l2
    assert ctrl.currentProject == l1
    assert ctrl.lastProject == l2

    ctrl.cycleProject()  # current=l2, last=l1
    assert ctrl.currentProject == l2
    assert ctrl.lastProject == l1


def test_cycle_project_noop_without_last(app_env):
    projects = ["/work/p1/.agents/skills"]
    ctrl = _make_controller(projects, _make_config(projects))

    # Only one project exists, so there is never a previous project.
    ctrl.cycleProject()
    assert ctrl.lastProject == ""


def test_last_project_persisted_and_restored(app_env):
    projects = ["/work/p1/.agents/skills", "/work/p2/.agents/skills"]
    config = _make_config(projects)
    ctrl = _make_controller(projects, config)
    l1 = project_label(projects[0])
    l2 = project_label(projects[1])

    ctrl.setCurrentProject(l2)
    assert config.get("last_project_label") == l1

    ctrl2 = _make_controller(projects, config)
    assert ctrl2.lastProject == l1


def test_last_project_changed_signal_emitted(app_env):
    projects = ["/work/p1/.agents/skills", "/work/p2/.agents/skills"]
    ctrl = _make_controller(projects, _make_config(projects))

    fired = []
    ctrl.lastProjectChanged.connect(lambda: fired.append(True))

    ctrl.setCurrentProject(project_label(projects[1]))
    assert fired and len(fired) == 1
