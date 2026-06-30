"""QSyntaxHighlighter subclass for highlighting skill references in QML TextArea.

Uses Qt-native syntax highlighting to paint character-range backgrounds
on a QTextDocument. Works with QQuickTextEdit (QML TextArea) via its
textDocument property.

Highlights are re-applied automatically when the document content changes.
"""

from __future__ import annotations

import logging

from PySide6.QtGui import QColor, QSyntaxHighlighter, QTextCharFormat

logger = logging.getLogger(__name__)

# Default accent colour — matches dark-mode Theme.accent (#3B82F6)
_DEFAULT_COLOR = "#3B82F6"


class SkillRefHighlighter(QSyntaxHighlighter):
    """Highlight skill reference character ranges in a QTextDocument.

    This is the correct way to highlight text in a QML TextArea —
    it works at the document level, scrolls with content, aligns to
    character cells, and supports multi-line ranges.
    """

    def __init__(self, document, accent_color: str | QColor | None = None) -> None:
        super().__init__(document)
        self._ranges: list[tuple[int, int]] = []  # (start, end) pairs
        self._focused_index: int = -1
        self._accent = QColor(self._resolve_color(accent_color))
        self._base_alpha: int = 80  # always-on translucent accent
        self._focus_alpha: int = 180  # stronger for focused match
        self._underline_alpha: int = 220

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_color(accent_color: str | QColor | None) -> str:
        """Resolve accent colour to a hex string."""
        if isinstance(accent_color, QColor):
            return accent_color.name()
        if isinstance(accent_color, str) and accent_color:
            return accent_color
        return _DEFAULT_COLOR

    def set_ranges(self, ranges: list[dict], focused_index: int = -1) -> None:
        """Set highlight ranges and trigger a re-highlight.

        Parameters
        ----------
        ranges : list[dict]
            Each dict must have ``start`` and ``end`` (int, character offsets
            in the full document content).
        focused_index : int
            Index to highlight with stronger focus (underline + higher alpha).
            Pass ``-1`` for no focus.
        """
        new_ranges = [(int(r["start"]), int(r["end"])) for r in ranges]
        if self._ranges == new_ranges and self._focused_index == focused_index:
            return
        self._ranges = new_ranges
        self._focused_index = focused_index
        self.rehighlight()
        logger.debug(
            "SkillRefHighlighter: rehighlight %d ranges (focused=%d)",
            len(self._ranges),
            self._focused_index,
        )

    def clear(self) -> None:
        """Remove all highlights."""
        if not self._ranges and self._focused_index == -1:
            return
        self._ranges = []
        self._focused_index = -1
        self.rehighlight()
        logger.debug("SkillRefHighlighter: cleared")

    # ------------------------------------------------------------------
    # QSyntaxHighlighter override
    # ------------------------------------------------------------------

    def highlightBlock(self, text: str) -> None:  # noqa: N802 (Qt naming)
        """Called by Qt for each text block during rehighlight."""
        if not self._ranges:
            return

        block_start = self.currentBlock().position()
        block_end = block_start + len(text)

        for i, (start, end) in enumerate(self._ranges):
            # Clip range to current block boundaries
            lo = max(start, block_start)
            hi = min(end, block_end)
            if lo >= hi:
                continue

            fmt = QTextCharFormat()

            # Background: translucent accent
            bg = QColor(self._accent)
            bg.setAlpha(self._focus_alpha if i == self._focused_index else self._base_alpha)
            fmt.setBackground(bg)

            # Focused range: underline accent
            if i == self._focused_index:
                fmt.setFontUnderline(True)
                underline_color = QColor(self._accent)
                underline_color.setAlpha(self._underline_alpha)
                fmt.setUnderlineColor(underline_color)

            # setFormat(offset_in_block, length, format)
            self.setFormat(lo - block_start, hi - lo, fmt)
