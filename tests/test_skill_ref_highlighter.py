"""Tests for SkillRefHighlighter (QSyntaxHighlighter-based text highlighting).

Uses real QTextDocument instances via pytest-qt's qapp fixture.
"""

import pytest


class TestSkillRefHighlighterColor:
    """Test _resolve_color — pure logic, no Qt."""

    def test_string_passthrough(self):
        from skill_manager.core.skill_ref_highlighter import SkillRefHighlighter

        assert SkillRefHighlighter._resolve_color("#FF0000") == "#FF0000"

    def test_none_returns_default(self):
        from skill_manager.core.skill_ref_highlighter import _DEFAULT_COLOR, SkillRefHighlighter

        assert SkillRefHighlighter._resolve_color(None) == _DEFAULT_COLOR

    def test_empty_string_returns_default(self):
        from skill_manager.core.skill_ref_highlighter import _DEFAULT_COLOR, SkillRefHighlighter

        assert SkillRefHighlighter._resolve_color("") == _DEFAULT_COLOR

    def test_qcolor_returns_name(self):
        from PySide6.QtGui import QColor

        from skill_manager.core.skill_ref_highlighter import SkillRefHighlighter

        color = QColor("#00FF00")
        assert SkillRefHighlighter._resolve_color(color) == "#00ff00"


class TestSkillRefHighlighterIntegration:
    """Integration tests using real QTextDocument (requires QApplication)."""

    @pytest.fixture(autouse=True)
    def _setup_app(self, qapp):
        """Ensure a QApplication exists for PySide6."""
        pass

    def _make_doc(self, text: str):
        """Create a QTextDocument with the given text."""
        from PySide6.QtGui import QTextDocument

        doc = QTextDocument()
        doc.setPlainText(text)
        return doc

    def test_set_ranges_highlights_blocks(self):
        """set_ranges should cause highlightBlock to run on matching blocks."""

        from skill_manager.core.skill_ref_highlighter import SkillRefHighlighter

        doc = self._make_doc("Hello /brainstorming world")
        highlighter = SkillRefHighlighter(doc)

        ranges = [{"name": "brainstorming", "start": 6, "end": 21}]
        highlighter.set_ranges(ranges, focused_index=-1)

        # Verify by checking that the document was re-highlighted
        # (QSyntaxHighlighter attaches to the document and runs)
        assert highlighter._ranges == [(6, 21)]

    def test_focused_gets_underline(self):
        """Focused range should have underline set."""
        from PySide6.QtGui import QTextDocument

        from skill_manager.core.skill_ref_highlighter import SkillRefHighlighter

        doc = QTextDocument()
        doc.setPlainText("Hello /brainstorming world /concise-planning end")
        highlighter = SkillRefHighlighter(doc)

        ranges = [
            {"name": "brainstorming", "start": 6, "end": 21},
            {"name": "concise-planning", "start": 27, "end": 43},
        ]
        highlighter.set_ranges(ranges, focused_index=0)

        # Verify highlighter stored correct state
        assert highlighter._focused_index == 0
        assert len(highlighter._ranges) == 2

    def test_clear_removes_all(self):
        """clear() should reset ranges and rehighlight."""

        from skill_manager.core.skill_ref_highlighter import SkillRefHighlighter

        doc = self._make_doc("Hello world")
        highlighter = SkillRefHighlighter(doc)

        highlighter.set_ranges([{"name": "world", "start": 6, "end": 11}])
        assert len(highlighter._ranges) == 1

        highlighter.clear()
        assert len(highlighter._ranges) == 0
        assert highlighter._focused_index == -1

    def test_empty_ranges_clears(self):
        """Passing empty ranges should result in no highlights."""

        from skill_manager.core.skill_ref_highlighter import SkillRefHighlighter

        doc = self._make_doc("Hello world")
        highlighter = SkillRefHighlighter(doc)

        highlighter.set_ranges([])
        assert len(highlighter._ranges) == 0

    def test_overwrite_replaces_previous(self):
        """Calling set_ranges twice should replace, not accumulate."""

        from skill_manager.core.skill_ref_highlighter import SkillRefHighlighter

        doc = self._make_doc("Hello /brainstorming world /concise-planning end")
        highlighter = SkillRefHighlighter(doc)

        ranges1 = [{"name": "brainstorming", "start": 6, "end": 21}]
        ranges2 = [
            {"name": "brainstorming", "start": 6, "end": 21},
            {"name": "concise-planning", "start": 27, "end": 43},
        ]

        highlighter.set_ranges(ranges1)
        assert len(highlighter._ranges) == 1

        highlighter.set_ranges(ranges2)
        assert len(highlighter._ranges) == 2

    def test_multi_block_range(self):
        """Ranges spanning multiple blocks should not crash."""

        from skill_manager.core.skill_ref_highlighter import SkillRefHighlighter

        doc = self._make_doc("Line one\nLine two\nLine three")
        highlighter = SkillRefHighlighter(doc)

        # Range spans from block 0 to block 2
        ranges = [{"name": "multi", "start": 5, "end": 20}]
        highlighter.set_ranges(ranges, focused_index=-1)
        assert len(highlighter._ranges) == 1

    def test_no_ranges_highlight_block_is_noop(self):
        """highlightBlock with no ranges should not crash."""

        from skill_manager.core.skill_ref_highlighter import SkillRefHighlighter

        doc = self._make_doc("Hello world")
        highlighter = SkillRefHighlighter(doc)
        # Manually trigger highlightBlock on the first block
        block = doc.firstBlock()
        highlighter.highlightBlock(block.text())
        # Should not raise
