"""Tests for broadened file watcher event handling (Fix 3).

Covers:
- on_deleted / on_moved handlers fire regardless of file extension
  (but only for relevant .agents paths — irrelevant paths are ignored)
- on_any_event still filters for directories and .md files within .agents
- Debounce still works for all event types
- Edge cases: None timer, rapid events, cancel during debounce
"""

from __future__ import annotations

import time
from pathlib import Path
from unittest.mock import MagicMock

from skill_manager.core.file_watch import SkillFolderEventHandler, SkillFolderWatcher

_AGENTS_PREFIX = "/tmp/proj/.agents/skills"


class TestOnDeletedAlwaysFires:
    """on_deleted must always trigger the callback for .agents paths, regardless of extension."""

    def test_on_deleted_fires_for_md_file(self):
        cb = MagicMock()
        h = SkillFolderEventHandler(cb, debounce_ms=0)
        evt = MagicMock()
        evt.is_directory = False
        evt.src_path = f"{_AGENTS_PREFIX}/my-skill/SKILL.md"
        h.on_deleted(evt)
        cb.assert_called_once_with(f"{_AGENTS_PREFIX}/my-skill/SKILL.md")

    def test_on_deleted_fires_for_non_md_file(self):
        cb = MagicMock()
        h = SkillFolderEventHandler(cb, debounce_ms=0)
        evt = MagicMock()
        evt.is_directory = False
        evt.src_path = f"{_AGENTS_PREFIX}/my-skill/README.txt"
        h.on_deleted(evt)
        cb.assert_called_once_with(f"{_AGENTS_PREFIX}/my-skill/README.txt")

    def test_on_deleted_fires_for_directory(self):
        cb = MagicMock()
        h = SkillFolderEventHandler(cb, debounce_ms=0)
        evt = MagicMock()
        evt.is_directory = True
        evt.src_path = f"{_AGENTS_PREFIX}/my-skill"
        h.on_deleted(evt)
        cb.assert_called_once_with(f"{_AGENTS_PREFIX}/my-skill")

    def test_on_deleted_fires_with_debounce(self):
        cb = MagicMock()
        h = SkillFolderEventHandler(cb, debounce_ms=50)
        evt = MagicMock()
        evt.is_directory = False
        evt.src_path = f"{_AGENTS_PREFIX}/some-file.json"
        h.on_deleted(evt)
        # Should schedule, not call immediately
        cb.assert_not_called()
        assert h._timer is not None
        h.cancel()

    def test_on_deleted_ignores_irrelevant_path(self):
        cb = MagicMock()
        h = SkillFolderEventHandler(cb, debounce_ms=0)
        evt = MagicMock()
        evt.is_directory = False
        evt.src_path = "/tmp/proj/frontend/README.txt"
        h.on_deleted(evt)
        cb.assert_not_called()


class TestOnMovedAlwaysFires:
    """on_moved must always trigger the callback for .agents paths, regardless of extension."""

    def test_on_moved_fires_for_md_file(self):
        cb = MagicMock()
        h = SkillFolderEventHandler(cb, debounce_ms=0)
        evt = MagicMock()
        evt.is_directory = False
        evt.src_path = f"{_AGENTS_PREFIX}/SKILL.md"
        evt.dest_path = f"{_AGENTS_PREFIX}/SKILL2.md"
        h.on_moved(evt)
        cb.assert_called_once_with(f"{_AGENTS_PREFIX}/SKILL.md")

    def test_on_moved_fires_for_non_md_file(self):
        cb = MagicMock()
        h = SkillFolderEventHandler(cb, debounce_ms=0)
        evt = MagicMock()
        evt.is_directory = False
        evt.src_path = f"{_AGENTS_PREFIX}/data.json"
        evt.dest_path = ""
        h.on_moved(evt)
        cb.assert_called_once_with(f"{_AGENTS_PREFIX}/data.json")

    def test_on_moved_fires_for_directory(self):
        cb = MagicMock()
        h = SkillFolderEventHandler(cb, debounce_ms=0)
        evt = MagicMock()
        evt.is_directory = True
        evt.src_path = f"{_AGENTS_PREFIX}/old-name"
        evt.dest_path = f"{_AGENTS_PREFIX}/new-name"
        h.on_moved(evt)
        cb.assert_called_once_with(f"{_AGENTS_PREFIX}/old-name")

    def test_on_moved_fires_when_dest_is_agents(self):
        """Move from irrelevant src to relevant dest must still fire."""
        cb = MagicMock()
        h = SkillFolderEventHandler(cb, debounce_ms=0)
        evt = MagicMock()
        evt.is_directory = False
        evt.src_path = "/tmp/proj/frontend/file.txt"
        evt.dest_path = f"{_AGENTS_PREFIX}/imported.md"
        h.on_moved(evt)
        cb.assert_called_once()

    def test_on_moved_ignores_irrelevant_paths(self):
        cb = MagicMock()
        h = SkillFolderEventHandler(cb, debounce_ms=0)
        evt = MagicMock()
        evt.is_directory = False
        evt.src_path = "/tmp/proj/frontend/file.txt"
        evt.dest_path = "/tmp/proj/backend/other.txt"
        h.on_moved(evt)
        cb.assert_not_called()


class TestOnAnyEventStillFilters:
    """on_any_event must still filter: only directories and .md files within .agents."""

    def test_on_any_event_fires_for_directory(self):
        cb = MagicMock()
        h = SkillFolderEventHandler(cb, debounce_ms=0)
        evt = MagicMock()
        evt.is_directory = True
        evt.src_path = f"{_AGENTS_PREFIX}/my-skill"
        h.on_any_event(evt)
        cb.assert_called_once()

    def test_on_any_event_fires_for_md_file(self):
        cb = MagicMock()
        h = SkillFolderEventHandler(cb, debounce_ms=0)
        evt = MagicMock()
        evt.is_directory = False
        evt.src_path = f"{_AGENTS_PREFIX}/my-skill/SKILL.md"
        h.on_any_event(evt)
        cb.assert_called_once()

    def test_on_any_event_ignores_non_md_file(self):
        cb = MagicMock()
        h = SkillFolderEventHandler(cb, debounce_ms=0)
        evt = MagicMock()
        evt.is_directory = False
        evt.src_path = f"{_AGENTS_PREFIX}/my-skill/data.json"
        h.on_any_event(evt)
        cb.assert_not_called()

    def test_on_any_event_ignores_irrelevant_md(self):
        cb = MagicMock()
        h = SkillFolderEventHandler(cb, debounce_ms=0)
        evt = MagicMock()
        evt.is_directory = False
        evt.src_path = "/tmp/proj/frontend/README.md"
        h.on_any_event(evt)
        cb.assert_not_called()

    def test_on_any_event_ignores_irrelevant_dir(self):
        cb = MagicMock()
        h = SkillFolderEventHandler(cb, debounce_ms=0)
        evt = MagicMock()
        evt.is_directory = True
        evt.src_path = "/tmp/proj/frontend"
        h.on_any_event(evt)
        cb.assert_not_called()


class TestDebounceForAllHandlers:
    """Debounce must work for on_deleted and on_moved too."""

    def test_on_deleted_debounce_coalesces(self):
        cb = MagicMock()
        h = SkillFolderEventHandler(cb, debounce_ms=100)
        for i in range(5):
            evt = MagicMock()
            evt.is_directory = False
            evt.src_path = f"{_AGENTS_PREFIX}/file-{i}.txt"
            h.on_deleted(evt)
        # All 5 should coalesce into one pending timer
        assert h._timer is not None
        h.cancel()

    def test_on_moved_debounce_coalesces(self):
        cb = MagicMock()
        h = SkillFolderEventHandler(cb, debounce_ms=100)
        for i in range(5):
            evt = MagicMock()
            evt.is_directory = True
            evt.src_path = f"{_AGENTS_PREFIX}/dir-{i}"
            evt.dest_path = f"{_AGENTS_PREFIX}/dir-{i}-new"
            h.on_moved(evt)
        assert h._timer is not None
        h.cancel()

    def test_mixed_handlers_share_debounce(self):
        """Different handler types should share the same debounce timer."""
        cb = MagicMock()
        h = SkillFolderEventHandler(cb, debounce_ms=100)
        # on_deleted
        evt1 = MagicMock()
        evt1.is_directory = False
        evt1.src_path = f"{_AGENTS_PREFIX}/file.txt"
        h.on_deleted(evt1)
        timer1 = h._timer
        assert timer1 is not None
        # Cancel and create new timer via on_moved — timer identity is
        # not guaranteed across cancel+reschedule, but the callback
        # should NOT fire yet.
        h.cancel()
        assert h._timer is None
        evt2 = MagicMock()
        evt2.is_directory = True
        evt2.src_path = f"{_AGENTS_PREFIX}/dir"
        evt2.dest_path = f"{_AGENTS_PREFIX}/dir2"
        h.on_moved(evt2)
        # Should have a new timer, callback not yet called
        assert h._timer is not None
        cb.assert_not_called()
        h.cancel()


class TestCancelAndFire:
    """Edge cases around cancel and fire."""

    def test_cancel_cleans_up(self):
        cb = MagicMock()
        h = SkillFolderEventHandler(cb, debounce_ms=200)
        evt = MagicMock()
        evt.is_directory = True
        evt.src_path = f"{_AGENTS_PREFIX}/something"
        h.on_any_event(evt)
        assert h._timer is not None
        h.cancel()
        assert h._timer is None
        cb.assert_not_called()

    def test_fire_resets_timer(self):
        """With debounce_ms=0, on_any_event fires immediately via _fire_or_schedule."""
        cb = MagicMock()
        h = SkillFolderEventHandler(cb, debounce_ms=0)
        evt = MagicMock()
        evt.is_directory = True
        evt.src_path = f"{_AGENTS_PREFIX}/something"
        h.on_any_event(evt)
        # debounce_ms=0 means _fire_or_schedule calls _callback directly
        cb.assert_called_once_with(f"{_AGENTS_PREFIX}/something")


class TestRelevanceAndDebounceInternals:
    """Cover _is_relevant_path batch and debounced _fire callback."""

    def test_is_relevant_batch(self):
        # "batch" coalesced callback literal is always relevant
        assert SkillFolderEventHandler._is_relevant_path("batch") is True
        assert SkillFolderEventHandler._is_relevant_path("BATCH") is True

    def test_is_relevant_agents_variants(self):
        assert SkillFolderEventHandler._is_relevant_path("/proj/.agents") is True
        assert SkillFolderEventHandler._is_relevant_path("/proj/.agents/skills/x.md") is True
        assert SkillFolderEventHandler._is_relevant_path("/proj/.AGENTS/commands") is True
        assert SkillFolderEventHandler._is_relevant_path("/proj/frontend/file.md") is False

    def test_debounced_fires_batch(self):
        cb = MagicMock()
        h = SkillFolderEventHandler(cb, debounce_ms=20)
        evt = MagicMock()
        evt.is_directory = True
        evt.src_path = f"{_AGENTS_PREFIX}/something"
        h.on_any_event(evt)
        assert h._timer is not None
        time.sleep(0.12)
        cb.assert_called_once_with("batch")
        assert h._timer is None

    def test_expand_watch_paths(self, tmp_path: Path):
        # empty and blank inputs
        assert SkillFolderWatcher._expand_watch_paths([]) == []
        assert SkillFolderWatcher._expand_watch_paths([""]) == []

        # plain path without .agents — returned as-is
        plain = tmp_path / "plain"
        plain.mkdir()
        assert SkillFolderWatcher._expand_watch_paths([str(plain)]) == [plain]

        # project root with .agents/skills and .agents/commands -> expands to both
        proj = tmp_path / "proj"
        agents = proj / ".agents"
        skills = agents / "skills"
        commands = agents / "commands"
        proj.mkdir()
        agents.mkdir()
        skills.mkdir()
        commands.mkdir()
        expanded = SkillFolderWatcher._expand_watch_paths([str(proj)])
        assert skills in expanded
        assert commands in expanded

        # project root with only .agents (no skills/commands) -> expands to .agents
        proj2 = tmp_path / "proj2"
        agents2 = proj2 / ".agents"
        proj2.mkdir()
        agents2.mkdir()
        expanded2 = SkillFolderWatcher._expand_watch_paths([str(proj2)])
        assert agents2 in expanded2

    def test_watcher_remove_and_stop_cover(self, tmp_path: Path):
        cb = MagicMock()
        d = tmp_path / "plain2"
        d.mkdir()
        w = SkillFolderWatcher([str(d)], cb)
        w.remove_path(str(d))
        w.stop()
        assert not w.started
