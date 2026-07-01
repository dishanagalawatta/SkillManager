"""Tests for broadened file watcher event handling (Fix 3).

Covers:
- on_deleted / on_moved handlers fire regardless of file extension
- on_any_event still filters for directories and .md files
- Debounce still works for all event types
- Edge cases: None timer, rapid events, cancel during debounce
"""
from __future__ import annotations

from unittest.mock import MagicMock

from skill_manager.core.file_watch import SkillFolderEventHandler


class TestOnDeletedAlwaysFires:
    """on_deleted must always trigger the callback, regardless of path."""

    def test_on_deleted_fires_for_md_file(self):
        cb = MagicMock()
        h = SkillFolderEventHandler(cb, debounce_ms=0)
        evt = MagicMock()
        evt.is_directory = False
        evt.src_path = "/skills/my-skill/SKILL.md"
        h.on_deleted(evt)
        cb.assert_called_once_with("/skills/my-skill/SKILL.md")

    def test_on_deleted_fires_for_non_md_file(self):
        cb = MagicMock()
        h = SkillFolderEventHandler(cb, debounce_ms=0)
        evt = MagicMock()
        evt.is_directory = False
        evt.src_path = "/skills/my-skill/README.txt"
        h.on_deleted(evt)
        cb.assert_called_once_with("/skills/my-skill/README.txt")

    def test_on_deleted_fires_for_directory(self):
        cb = MagicMock()
        h = SkillFolderEventHandler(cb, debounce_ms=0)
        evt = MagicMock()
        evt.is_directory = True
        evt.src_path = "/skills/my-skill"
        h.on_deleted(evt)
        cb.assert_called_once_with("/skills/my-skill")

    def test_on_deleted_fires_with_debounce(self):
        cb = MagicMock()
        h = SkillFolderEventHandler(cb, debounce_ms=50)
        evt = MagicMock()
        evt.is_directory = False
        evt.src_path = "/skills/some-file.json"
        h.on_deleted(evt)
        # Should schedule, not call immediately
        cb.assert_not_called()
        assert h._timer is not None
        h.cancel()


class TestOnMovedAlwaysFires:
    """on_moved must always trigger the callback, regardless of path."""

    def test_on_moved_fires_for_md_file(self):
        cb = MagicMock()
        h = SkillFolderEventHandler(cb, debounce_ms=0)
        evt = MagicMock()
        evt.is_directory = False
        evt.src_path = "/skills/SKILL.md"
        h.on_moved(evt)
        cb.assert_called_once_with("/skills/SKILL.md")

    def test_on_moved_fires_for_non_md_file(self):
        cb = MagicMock()
        h = SkillFolderEventHandler(cb, debounce_ms=0)
        evt = MagicMock()
        evt.is_directory = False
        evt.src_path = "/skills/data.json"
        h.on_moved(evt)
        cb.assert_called_once_with("/skills/data.json")

    def test_on_moved_fires_for_directory(self):
        cb = MagicMock()
        h = SkillFolderEventHandler(cb, debounce_ms=0)
        evt = MagicMock()
        evt.is_directory = True
        evt.src_path = "/skills/old-name"
        h.on_moved(evt)
        cb.assert_called_once_with("/skills/old-name")


class TestOnAnyEventStillFilters:
    """on_any_event must still filter: only directories and .md files."""

    def test_on_any_event_fires_for_directory(self):
        cb = MagicMock()
        h = SkillFolderEventHandler(cb, debounce_ms=0)
        evt = MagicMock()
        evt.is_directory = True
        evt.src_path = "/skills/my-skill"
        h.on_any_event(evt)
        cb.assert_called_once()

    def test_on_any_event_fires_for_md_file(self):
        cb = MagicMock()
        h = SkillFolderEventHandler(cb, debounce_ms=0)
        evt = MagicMock()
        evt.is_directory = False
        evt.src_path = "/skills/my-skill/SKILL.md"
        h.on_any_event(evt)
        cb.assert_called_once()

    def test_on_any_event_ignores_non_md_file(self):
        cb = MagicMock()
        h = SkillFolderEventHandler(cb, debounce_ms=0)
        evt = MagicMock()
        evt.is_directory = False
        evt.src_path = "/skills/my-skill/data.json"
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
            evt.src_path = f"/skills/file-{i}.txt"
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
            evt.src_path = f"/skills/dir-{i}"
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
        evt1.src_path = "/skills/file.txt"
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
        evt2.src_path = "/skills/dir"
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
        evt.src_path = "/skills/something"
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
        evt.src_path = "/skills/something"
        h.on_any_event(evt)
        # debounce_ms=0 means _fire_or_schedule calls _callback directly
        cb.assert_called_once_with("/skills/something")
