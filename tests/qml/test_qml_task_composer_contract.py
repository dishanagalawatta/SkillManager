"""QML contract for the inline task composer.

The composer replaced the one-line "type in a pill, press Enter" quick-add: a
task is now written where it lands (multi-line title + notes, bullet subtasks,
image attachments, priority). These assertions pin the behaviour that makes
that possible, because a silent regression here turns the whole panel back into
a single-line field the user cannot grow.
"""

from pathlib import Path

QML_DIR = (
    Path(__file__).resolve().parent.parent.parent
    / "src"
    / "skill_manager"
    / "SkillManagerComponents"
)


def _read(*parts: str) -> str:
    return QML_DIR.joinpath(*parts).read_text(encoding="utf-8")


def _strip_comments(source: str) -> str:
    """Drop // and /* */ comments so assertions target live code only."""
    lines = []
    in_block = False
    for line in source.splitlines():
        if in_block:
            if "*/" in line:
                in_block = False
            continue
        if line.strip().startswith("/*"):
            in_block = "*/" not in line
            continue
        if "//" in line:
            line = line.split("//", 1)[0]
        lines.append(line)
    return "\n".join(lines)


def _composer() -> str:
    return _strip_comments(_read("TaskComposer.qml"))


def test_composer_is_registered():
    qmldir = _read("qmldir")
    assert "TaskComposer 1.0 TaskComposer.qml" in qmldir
    assert (QML_DIR / "TaskComposer.qml").exists()


def test_composer_is_a_multi_line_editor():
    """A task can be one line or a title plus notes — never a forced one-liner."""
    composer = _composer()

    assert "TextArea {" in composer
    assert "TextField {" not in composer
    assert "wrapMode: TextArea.Wrap" in composer
    assert "Layout.preferredHeight: Math.min(" in composer
    # It grows while typing, then scrolls instead of eating the whole panel.
    assert "180" in composer
    assert "placeholderText:" in composer


def test_composer_splits_title_and_notes():
    """First non-empty line is the title; the rest becomes the notes."""
    composer = _composer()

    assert "function _split()" in composer
    assert "return { title: title, notes: notes }" in composer
    assert (
        "signal submitted(string title, string notes, string priority, var attachments)" in composer
    )


def test_composer_keyboard_contract():
    """Ctrl+Enter adds, Enter makes a newline, Esc discards."""
    composer = _composer()

    assert "Qt.Key_Return" in composer
    assert "Qt.Key_Enter" in composer
    assert "Qt.ControlModifier" in composer
    assert "Qt.MetaModifier" in composer
    assert "Qt.Key_Escape" in composer
    assert "signal cancelled()" in composer


def test_enter_continues_bullet_lists():
    """`- ` and `- [ ] ` subtasks continue on Enter and end on an empty line."""
    composer = _composer()

    assert "function _bulletPrefix()" in composer
    assert "function _stripEmptyBullet()" in composer
    assert "editor.insert(editor.cursorPosition" in composer
    assert "editor.remove(lineStart, pos)" in composer


def test_priority_can_be_cycled_in_place():
    composer = _composer()

    assert "function _cyclePriority()" in composer
    assert 'root.priority === "low" ? "medium"' in composer
    assert "Accessible.onPressAction: root._cyclePriority()" in composer
    assert "Accessible.onToggleAction: root._cyclePriority()" in composer


def test_images_can_be_attached_three_ways():
    """File dialog, drag-and-drop, and Ctrl+V of a clipboard image."""
    composer = _composer()

    assert "FileDialog {" in composer
    assert "nameFilters:" in composer
    assert "DropArea {" in composer
    assert "onDropped:" in composer
    assert "Qt.Key_V" in composer
    assert "attachClipboardImage(" in composer
    assert "attachTaskImage(" in composer
    # A dropped non-image must say so instead of vanishing.
    assert "function _fail(" in composer
    assert "Only image files can be attached" in composer


def test_attachments_render_as_removable_thumbnails():
    composer = _composer()

    assert "Repeater {" in composer
    assert "Image {" in composer
    assert "PreserveAspectCrop" in composer
    assert "function _removeAttachment(index)" in composer


def test_composer_is_accessible():
    composer = _composer()

    assert "Accessible.role: Accessible.EditableText" in composer
    assert "Accessible.role: Accessible.Button" in composer
    assert "Accessible.name:" in composer
    assert 'objectName: "taskAttachBtn"' in composer
    assert 'objectName: "taskComposerAddBtn"' in composer


def test_composer_uses_theme_tokens_only():
    """No hardcoded colours — the composer must follow the theme."""
    source = _read("TaskComposer.qml")

    assert "#" not in source.replace("# ", ""), "hardcoded colour in the task composer"


def test_composer_is_disabled_without_a_project():
    composer = _composer()

    assert 'enabled: root.projectPath !== ""' in composer
    assert "Select a project to add tasks" in composer
    assert "readonly property bool canSubmit:" in composer
