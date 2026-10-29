"""QML contract: command groups use the shared command glyph.

Commands are filed under the ``Special`` main category and grouped by their own
frontmatter ``category``.  The section header therefore used to paint that
*category's* emoji (🧪 for "Testing", 💼 for "Workflow", …) on top of a group
that contains nothing but commands.  Every command group now shows one shared
glyph — the 📜 command emoji from ``Theme.commandEmoji`` — and only non-command
sections keep their category emoji.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
QML_DIR = ROOT / "src" / "skill_manager" / "SkillManagerComponents"


def _strip_comments(text: str) -> str:
    without_block = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    return re.sub(r"//[^\n]*", "", without_block)


def test_command_sections_render_the_shared_glyph():
    item = _strip_comments((QML_DIR / "SkillItem.qml").read_text(encoding="utf-8"))

    assert "readonly property bool isCommandSection" in item
    assert "model.isCommand" in item
    assert "text: Theme.commandEmoji" in item
    # The dedicated SVG glyph is gone; the emoji is the one command icon.
    assert "command-icon.svg" not in item


def test_category_emoji_is_suppressed_for_command_sections():
    """Both glyphs sit in the same RowLayout, so both need explicit gating."""
    item = _strip_comments((QML_DIR / "SkillItem.qml").read_text(encoding="utf-8"))

    # The emoji Text is hidden for command sections...
    assert "visible: !root.isCommandSection" in item
    # ...and the shared glyph is hidden for everything else.
    assert "visible: root.isCommandSection" in item
    assert "AppController.getCategoryEmoji(root.subCat)" in item
