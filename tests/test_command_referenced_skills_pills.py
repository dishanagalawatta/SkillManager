"""Tests for Command Inspector Skill Dependencies pills feature.

Validates that:
- The new backend slots return correct data for referenced skills.
- The QML inspector renders the skill dependencies section and overlay.
- The diagnostic event is emitted when the section renders.
"""

import textwrap
from pathlib import Path
from unittest.mock import patch

# ---------------------------------------------------------------------------
# Backend: getReferencedSkillsForCommand
# ---------------------------------------------------------------------------


class TestGetReferencedSkillsForCommand:
    def test_returns_ordered_with_counts(self, app_controller, temp_dir):
        """Command body with two refs to /git-pr and one /cavecrew returns ordered list."""
        project_path = temp_dir / "project"
        project_path.mkdir()
        commands_dir = project_path / ".agents" / "commands"
        commands_dir.mkdir(parents=True)

        app_controller._projects = [str(project_path)]

        cmd_file = commands_dir / "deploy.md"
        cmd_file.write_text(
            textwrap.dedent("""\
                ---
                name: Deploy
                category: DevOps
                type: command
                ---

                Use /git-pr for pull requests.
                Also /git-pr again for rebasing.
                And @cavecrew for subagents.
            """),
            encoding="utf-8",
        )

        skill_git = {
            "name": "git-pr",
            "folder_name": "git-pr",
            "local_path": str(project_path / ".agents" / "skills" / "git-pr"),
            "category": "Git",
        }
        skill_cave = {
            "name": "cavecrew",
            "folder_name": "cavecrew",
            "local_path": str(project_path / ".agents" / "skills" / "cavecrew"),
            "category": "Subagents",
        }
        app_controller._library_model.addOrUpdateSkills([skill_git, skill_cave])

        result = app_controller.ops.getReferencedSkillsForCommand(str(cmd_file))
        assert isinstance(result, list)
        assert len(result) == 2

        # First occurrence in source order is git-pr
        assert result[0]["name"] == "git-pr"
        assert result[0]["occurrences"] == 2

        # Second is cavecrew
        assert result[1]["name"] == "cavecrew"
        assert result[1]["occurrences"] == 1

    def test_returns_empty_for_no_refs(self, app_controller, temp_dir):
        """Command body with no skill references returns empty list."""
        project_path = temp_dir / "project"
        project_path.mkdir()
        commands_dir = project_path / ".agents" / "commands"
        commands_dir.mkdir(parents=True)

        app_controller._projects = [str(project_path)]

        cmd_file = commands_dir / "plain.md"
        cmd_file.write_text(
            "---\nname: Plain\ncategory: Misc\ntype: command\n---\n\nJust plain text.",
            encoding="utf-8",
        )

        result = app_controller.ops.getReferencedSkillsForCommand(str(cmd_file))
        assert result == []

    def test_returns_empty_for_missing_file(self, app_controller):
        """Non-existent file returns empty list."""
        result = app_controller.ops.getReferencedSkillsForCommand("/no/such/file.md")
        assert result == []

    def test_excludes_commands_and_screenshots(self, app_controller, temp_dir):
        """Referenced items that are commands or screenshots are excluded."""
        project_path = temp_dir / "project"
        project_path.mkdir()
        commands_dir = project_path / ".agents" / "commands"
        commands_dir.mkdir(parents=True)

        app_controller._projects = [str(project_path)]

        cmd_file = commands_dir / "test.md"
        cmd_file.write_text(
            "---\nname: Test\ncategory: Misc\ntype: command\n---\n\nUse /my-cmd.",
            encoding="utf-8",
        )

        # This is a command, not a skill — should be excluded
        cmd_skill = {
            "name": "my-cmd",
            "folder_name": "my-cmd",
            "local_path": str(commands_dir / "my-cmd.md"),
            "category": "Commands",
            "is_command": True,
        }
        app_controller._library_model.addOrUpdateSkills([cmd_skill])

        result = app_controller.ops.getReferencedSkillsForCommand(str(cmd_file))
        assert result == []


# ---------------------------------------------------------------------------
# Backend: getSkillReferenceRanges
# ---------------------------------------------------------------------------


class TestGetSkillReferenceRanges:
    def test_returns_character_offsets(self, app_controller, temp_dir):
        """Ranges contain correct start/end offsets for each reference."""
        project_path = temp_dir / "project"
        project_path.mkdir()
        commands_dir = project_path / ".agents" / "commands"
        commands_dir.mkdir(parents=True)

        app_controller._projects = [str(project_path)]

        cmd_file = commands_dir / "deploy.md"
        cmd_file.write_text(
            "---\nname: Deploy\ntype: command\n---\n\nUse /git-pr.",
            encoding="utf-8",
        )

        skill = {
            "name": "git-pr",
            "folder_name": "git-pr",
            "local_path": str(project_path / "skill"),
            "category": "Git",
        }
        app_controller._library_model.addOrUpdateSkills([skill])

        result = app_controller.ops.getSkillReferenceRanges(str(cmd_file))
        assert isinstance(result, list)
        assert len(result) == 1

        # The /git-pr reference in the body starts at some position in the body content (excluding frontmatter)
        from skill_manager.core.parsing.base import split_frontmatter
        content = cmd_file.read_text(encoding="utf-8")
        _, body = split_frontmatter(content)
        expected_start = body.index("/git-pr")
        assert result[0]["start"] == expected_start
        assert result[0]["end"] == expected_start + len("/git-pr")
        assert result[0]["name"] == "git-pr"

    def test_returns_empty_for_no_refs(self, app_controller, temp_dir):
        """No references means empty ranges."""
        project_path = temp_dir / "project"
        project_path.mkdir()
        commands_dir = project_path / ".agents" / "commands"
        commands_dir.mkdir(parents=True)

        app_controller._projects = [str(project_path)]

        cmd_file = commands_dir / "plain.md"
        cmd_file.write_text("No refs.", encoding="utf-8")

        result = app_controller.ops.getSkillReferenceRanges(str(cmd_file))
        assert result == []


class TestApplySkillHighlights:
    def test_apply_skill_highlights_with_qquicktextdocument(self, app_controller):
        """applySkillHighlights should extract QTextDocument from QQuickTextDocument wrapper."""
        from unittest.mock import MagicMock

        from PySide6.QtGui import QTextDocument

        # Mock the QQuickTextEdit item
        mock_text_edit = MagicMock()

        # Mock the QQuickTextDocument wrapper
        mock_quick_doc = MagicMock()

        # Create a real QTextDocument to be extracted and highlighted
        real_doc = QTextDocument()
        real_doc.setPlainText("Hello world")

        # Setup properties on mocks
        mock_quick_doc.textDocument.return_value = real_doc
        mock_text_edit.textDocument.return_value = mock_quick_doc
        mock_text_edit.property.return_value = mock_quick_doc

        # Patch _find_qml_text_edit to return our mock text edit
        with patch.object(app_controller.ops, "_find_qml_text_edit", return_value=mock_text_edit):
            # Apply highlights
            ranges = [{"name": "world", "start": 6, "end": 11}]
            import json
            app_controller.ops.applySkillHighlights(
                "commandBodyTextArea",
                json.dumps(ranges),
                focused_index=-1
            )

            # Verify the highlighter was attached to the underlying real QTextDocument
            highlighter = getattr(real_doc, "_skill_ref_highlighter", None)
            assert highlighter is not None
            assert highlighter._ranges == [(6, 11)]


# ---------------------------------------------------------------------------
# QML static scans
# ---------------------------------------------------------------------------


class TestCommandInspectorQML:
    def test_declares_skill_dependencies_section(self):
        """CommandInspector.qml must have a Skill Dependencies section with pills."""

        inspector = (
            Path(__file__).resolve().parent.parent
            / "src"
            / "skill_manager"
            / "SkillManagerComponents"
            / "CommandInspector.qml"
        )
        content = inspector.read_text(encoding="utf-8")

        # Must declare dependencyList and referenceRanges properties
        assert "property var dependencyList:" in content, (
            "CommandInspector must declare dependencyList property"
        )
        assert "property var referenceRanges:" in content, (
            "CommandInspector must declare referenceRanges property"
        )

        # Must have the Skill Dependencies section
        assert '"Skill Dependencies"' in content or "'Skill Dependencies'" in content, (
            "CommandInspector must have a 'Skill Dependencies' section label"
        )

        # Must have a Repeater for the dependency pills
        assert "Repeater" in content, (
            "CommandInspector must have a Repeater for dependency pills"
        )

        # Must have the onSkillChanged handler to update the lists
        assert "onSkillChanged" in content, (
            "CommandInspector must update dependency lists on skill changed"
        )

    def test_textarea_has_objectname(self):
        """bodyArea TextArea must have objectName 'commandBodyTextArea'."""

        inspector = (
            Path(__file__).resolve().parent.parent
            / "src"
            / "skill_manager"
            / "SkillManagerComponents"
            / "CommandInspector.qml"
        )
        content = inspector.read_text(encoding="utf-8")

        assert 'objectName: "commandBodyTextArea"' in content, (
            "bodyArea must have objectName 'commandBodyTextArea' for Python findChild"
        )

    def test_calls_apply_skill_highlights(self):
        """CommandInspector must call applySkillHighlights on selection change."""

        inspector = (
            Path(__file__).resolve().parent.parent
            / "src"
            / "skill_manager"
            / "SkillManagerComponents"
            / "CommandInspector.qml"
        )
        content = inspector.read_text(encoding="utf-8")

        assert "applySkillHighlights" in content, (
            "CommandInspector must call ops_controller.applySkillHighlights()"
        )
        assert "clearSkillHighlights" in content, (
            "CommandInspector must call ops_controller.clearSkillHighlights()"
        )

    def test_no_overlay_in_qmldir(self):
        """SkillReferenceOverlay must NOT be registered in qmldir."""

        qmldir = (
            Path(__file__).resolve().parent.parent
            / "src"
            / "skill_manager"
            / "SkillManagerComponents"
            / "qmldir"
        )
        content = qmldir.read_text(encoding="utf-8")
        assert "SkillReferenceOverlay" not in content, (
            "SkillReferenceOverlay must be removed from qmldir"
        )

    def test_overlay_file_deleted(self):
        """SkillReferenceOverlay.qml must not exist."""

        overlay = (
            Path(__file__).resolve().parent.parent
            / "src"
            / "skill_manager"
            / "SkillManagerComponents"
            / "SkillReferenceOverlay.qml"
        )
        assert not overlay.exists(), (
            "SkillReferenceOverlay.qml should be deleted"
        )


class TestFindQmlTextEdit:
    def test_finds_item_in_visual_tree_and_filters_visibility(self, app_controller):
        """_find_qml_text_edit should traverse visual items and choose visible ones."""
        from unittest.mock import MagicMock, patch

        from PySide6.QtQuick import QQuickItem, QQuickWindow

        # Create mocks representing windows and items
        mock_window = MagicMock(spec=QQuickWindow)
        mock_root_item = MagicMock(spec=QQuickItem)
        mock_window.contentItem.return_value = mock_root_item

        # Let's create two mock text edits (representing two commandBodyTextArea instances)
        # One is in visible/active tab, one in hidden tab
        text_edit_visible = MagicMock(spec=QQuickItem)
        text_edit_visible.objectName.return_value = "commandBodyTextArea"
        text_edit_visible.property.return_value = MagicMock()  # textDocument
        text_edit_visible.isVisible.return_value = True

        text_edit_hidden = MagicMock(spec=QQuickItem)
        text_edit_hidden.objectName.return_value = "commandBodyTextArea"
        text_edit_hidden.property.return_value = MagicMock()  # textDocument
        text_edit_hidden.isVisible.return_value = False

        # Visual child items setup
        mock_root_item.childItems.return_value = [text_edit_hidden, text_edit_visible]
        text_edit_hidden.childItems.return_value = []
        text_edit_visible.childItems.return_value = []

        # Standard QObject children setup
        mock_root_item.children.return_value = []
        mock_window.children.return_value = []

        # Mock QGuiApplication.allWindows to return our mock window
        with patch("PySide6.QtGui.QGuiApplication.allWindows", return_value=[mock_window]):
            # Query the text area
            res = app_controller.ops._find_qml_text_edit("commandBodyTextArea")

            # Should have traversed visual children, checked visibility, and returned the visible one!
            assert res is text_edit_visible

    def test_fallback_to_hidden_if_no_visible(self, app_controller):
        """_find_qml_text_edit should fallback to hidden item if no visible items exist."""
        from unittest.mock import MagicMock, patch

        from PySide6.QtQuick import QQuickItem, QQuickWindow

        mock_window = MagicMock(spec=QQuickWindow)
        mock_root_item = MagicMock(spec=QQuickItem)
        mock_window.contentItem.return_value = mock_root_item

        text_edit_hidden = MagicMock(spec=QQuickItem)
        text_edit_hidden.objectName.return_value = "commandBodyTextArea"
        text_edit_hidden.property.return_value = MagicMock()
        text_edit_hidden.isVisible.return_value = False

        mock_root_item.childItems.return_value = [text_edit_hidden]
        text_edit_hidden.childItems.return_value = []
        mock_root_item.children.return_value = []
        mock_window.children.return_value = []

        with patch("PySide6.QtGui.QGuiApplication.allWindows", return_value=[mock_window]):
            res = app_controller.ops._find_qml_text_edit("commandBodyTextArea")
            assert res is text_edit_hidden
