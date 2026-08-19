"""Tests for the per-command emoji customization feature.

The feature stores an emoji override for commands in app config (NOT in the
command's .md file).  QML reads ``model.emoji`` (mapped to ``EmojiRole``) for
command rows; ``SkillItem.qml`` falls back to ``"⚡"`` when ``model.emoji`` is
falsy.  The default command emoji is ``"⚡"``.

Covers:
  * ``ConfigManager`` emoji override + recents API
  * ``SkillModel.EmojiRole`` resolution in ``data()`` / ``roleNames()``
  * ``AppController`` emoji slots
"""

import os
from unittest.mock import patch

import pytest
from PySide6.QtTest import QSignalSpy

from skill_manager.app import AppController
from skill_manager.core.models.entities import Skill
from skill_manager.core.models.qt_model import SkillModel
from skill_manager.utils.task_runner import SynchronousTaskRunner

DEFAULT_EMOJI = "⚡"


# ---------------------------------------------------------------------------
# 1. ConfigManager
# ---------------------------------------------------------------------------


@pytest.fixture
def emoji_config(mock_config):
    """A real ConfigManager backed by a temp data dir (from conftest)."""
    return mock_config


def test_set_then_get_returns_emoji(emoji_config):
    emoji_config.set_command_emoji("/some/cmd", "🔥")
    assert emoji_config.get_command_emoji("/some/cmd") == "🔥"


def test_get_uses_normpath(emoji_config):
    # A path and its normalized form must resolve to the same override.
    raw = "/some/cmd/../cmd"
    emoji_config.set_command_emoji(raw, "🚀")
    assert emoji_config.get_command_emoji(os.path.normpath(raw)) == "🚀"
    assert emoji_config.get_command_emoji(raw) == "🚀"


def test_get_without_override_returns_default(emoji_config):
    assert emoji_config.get_command_emoji("/never/set") == DEFAULT_EMOJI


def test_set_empty_or_default_clears_override(emoji_config):
    emoji_config.set_command_emoji("/cmd", "🔥")
    assert emoji_config.get_command_emoji("/cmd") == "🔥"

    emoji_config.set_command_emoji("/cmd", "")
    assert "/cmd" not in emoji_config.data.get("command_emoji_overrides", {})
    assert emoji_config.get_command_emoji("/cmd") == DEFAULT_EMOJI

    # Re-set then clear via the default emoji sentinel.
    emoji_config.set_command_emoji("/cmd", "💡")
    emoji_config.set_command_emoji("/cmd", DEFAULT_EMOJI)
    assert "/cmd" not in emoji_config.data.get("command_emoji_overrides", {})


def test_clear_command_emoji_removes_it(emoji_config):
    emoji_config.set_command_emoji("/cmd", "🔥")
    emoji_config.clear_command_emoji("/cmd")
    assert "/cmd" not in emoji_config.data.get("command_emoji_overrides", {})
    assert emoji_config.get_command_emoji("/cmd") == DEFAULT_EMOJI


def test_emoji_recents_insert_front_dedupes_caps(emoji_config):
    # Insert several, with a duplicate, and verify front-insertion + dedup.
    for e in ["🔥", "🚀", "💡", "🔥", "⭐"]:
        emoji_config.add_emoji_recent(e)

    recents = emoji_config.get_emoji_recents()
    # Most-recent-first: last inserted "⭐" should be at the front.
    assert recents[0] == "⭐"
    # Deduped: "🔥" appears only once.
    assert recents.count("🔥") == 1
    # Capped at 16.
    assert len(recents) <= 16


def test_emoji_recents_caps_at_sixteen(emoji_config):
    for i in range(25):
        emoji_config.add_emoji_recent(f"e{i}")
    recents = emoji_config.get_emoji_recents()
    assert len(recents) == 16
    # Most recently added ("e24") is first.
    assert recents[0] == "e24"


# ---------------------------------------------------------------------------
# 2. SkillModel EmojiRole
# ---------------------------------------------------------------------------


@pytest.fixture
def emoji_model(emoji_config):
    return SkillModel(config=emoji_config)


def _command_skill(local_path, name="Cmd"):
    return Skill(name=name, local_path=local_path, is_command=True, category="Commands")


def _non_command_skill(local_path, name="Skill"):
    return Skill(name=name, local_path=local_path, is_command=False, category="Dev")


def test_role_names_contains_emoji(emoji_model):
    values = [bytes(v).decode("utf-8") for v in emoji_model.roleNames().values()]
    assert "emoji" in values


def test_data_emoji_override_returned(emoji_model, emoji_config):
    emoji_config.set_command_emoji("/cmd/a", "🔥")
    emoji_model._filtered_skills = [_command_skill("/cmd/a")]
    idx = emoji_model.index(0, 0)
    assert emoji_model.data(idx, emoji_model.EmojiRole) == "🔥"


def test_data_emoji_no_override_returns_default(emoji_model):
    emoji_model._filtered_skills = [_command_skill("/cmd/b")]
    idx = emoji_model.index(0, 0)
    assert emoji_model.data(idx, emoji_model.EmojiRole) == DEFAULT_EMOJI


def test_data_emoji_non_command_returns_none(emoji_model):
    emoji_model._filtered_skills = [_non_command_skill("/skill/c")]
    idx = emoji_model.index(0, 0)
    assert emoji_model.data(idx, emoji_model.EmojiRole) is None


def test_refresh_emoji_for_path_emits_data_changed(emoji_model, emoji_config, qtbot):
    path = "/cmd/refresh"
    emoji_model._filtered_skills = [_command_skill(path)]
    emoji_model._all_skills = emoji_model._filtered_skills

    spy = QSignalSpy(emoji_model.dataChanged)
    emoji_config.set_command_emoji(path, "🌟")
    emoji_model.refresh_emoji_for_path(path)

    # A dataChanged signal carrying the EmojiRole must have been emitted.
    assert spy.count() >= 1
    emitted_emoji_role = False
    for i in range(spy.count()):
        args = spy.at(i)
        # args[2] is the list of changed roles (may be empty for "all roles").
        roles = args[2] if len(args) > 2 else []
        if not roles or emoji_model.EmojiRole in roles:
            emitted_emoji_role = True
    assert emitted_emoji_role

    # The row now reflects the updated override.
    idx = emoji_model.index(0, 0)
    assert emoji_model.data(idx, emoji_model.EmojiRole) == "🌟"


# ---------------------------------------------------------------------------
# 3. AppController slots
# ---------------------------------------------------------------------------


@pytest.fixture
def emoji_controller(qapp, mock_config, temp_dir):
    """A full AppController (mirrors tests/test_app_controller.py setup)."""
    config_data = {
        "sources": [str(temp_dir / "lib")],
        "projects": [str(temp_dir / "proj")],
        "client_format": "Antigravity",
    }

    def mock_load_side_effect(self):
        self.data = dict(config_data)
        return self.data

    with patch(
        "skill_manager.core.config.ConfigManager.load",
        autospec=True,
        side_effect=mock_load_side_effect,
    ):
        (temp_dir / "lib").mkdir(exist_ok=True)
        (temp_dir / "proj").mkdir(exist_ok=True)
        c = AppController(skip_initial_load=True)
        c.task_runner = SynchronousTaskRunner()
        c._sources = config_data["sources"]
        c._projects = config_data["projects"]
        c._client_format = config_data["client_format"]
        yield c
        c.on_quit()


def _seed_command_in_library_model(controller, local_path):
    """Append a command Skill to the library model so EmojiRole resolves."""
    model = controller.libraryModel
    skill = _command_skill(local_path)
    model._all_skills = [skill]
    model._filtered_skills = [skill]


def test_controller_set_emoji_default_clears_override(emoji_controller):
    path = "/cmd/ctrl1"
    emoji_controller.setCommandEmoji(path, "🔥")
    assert emoji_controller.getCommandEmoji(path) == "🔥"

    # Setting the default emoji clears the override (no override stored).
    emoji_controller.setCommandEmoji(path, DEFAULT_EMOJI)
    overrides = emoji_controller._config.data.get("command_emoji_overrides", {})
    assert path not in overrides
    assert emoji_controller.getCommandEmoji(path) == DEFAULT_EMOJI


def test_controller_set_emoji_stores_and_model_returns_it(emoji_controller):
    path = "/cmd/ctrl2"
    _seed_command_in_library_model(emoji_controller, path)

    emoji_controller.setCommandEmoji(path, "🔥")
    assert emoji_controller.getCommandEmoji(path) == "🔥"

    idx = emoji_controller.skillModel.index(0, 0)
    assert emoji_controller.skillModel.data(idx, emoji_controller.skillModel.EmojiRole) == "🔥"


def test_controller_clear_emoji(emoji_controller):
    path = "/cmd/ctrl3"
    emoji_controller.setCommandEmoji(path, "🔥")
    assert emoji_controller.getCommandEmoji(path) == "🔥"
    emoji_controller.clearCommandEmoji(path)
    assert emoji_controller.getCommandEmoji(path) == DEFAULT_EMOJI


def test_controller_emoji_recents_round_trip(emoji_controller):
    emoji_controller.addEmojiRecent("🔥")
    emoji_controller.addEmojiRecent("🚀")
    recents = emoji_controller.getEmojiRecents()
    assert recents[0] == "🚀"
    assert "🔥" in recents
