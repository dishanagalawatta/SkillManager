"""Clipboard operations for the OpsController."""

import logging

from PySide6.QtCore import Slot

from skill_manager.controllers.ops._helpers import QTimer, _get_item_attr

logger = logging.getLogger(__name__)


class ClipboardMixin:
    """Copy skill references/text to the system clipboard."""

    def _maybeMinimizeOnCopy(self):
        """Requests app minimization if the setting is enabled and current view is QuickCopy."""
        if (
            self.app.config_controller.autoMinimizeOnQuickCopy
            and self.app.ui_controller.currentView == "QuickCopy"
        ):
            self.minimizeAppRequested.emit()
            logger.info("Auto-minimize on Quick Copy triggered.")

    @Slot(str)
    def copySkillToClipboard(self, path: str):
        """Finds skill by path and copies its reference to clipboard."""
        skill = next(
            (s for s in self.app.skillModel._all_skills if _get_item_attr(s, "local_path") == path),
            None,
        )
        if skill:
            self.copySkillReference(skill)  # type: ignore[arg-type]
        else:
            self.copyTextToClipboard(path)

    @Slot()
    def copyCurrentSelectionOrFocusedSkill(self):
        """Orchestrates copying based on selection or focus."""
        if self.app.skillModel.selectedCount > 0:
            self.copySelectedSkillsToClipboard()
            return
        selected = self.app._selected_skill
        if isinstance(selected, dict) and selected.get("local_path"):
            self.copySkillReference(selected)
            return
        if hasattr(selected, "local_path") and selected.local_path:
            data = {
                "local_path": selected.local_path,
                "name": selected.name,
                "body_content": selected.body_content,
                "description": selected.description,
                "is_command": selected.is_command,
                "is_screenshot": selected.is_screenshot,
            }
            self.copySkillReference(data)
            return
        first_skill = self.app.skillModel.get_skill_at(0)
        if first_skill:
            self.copySkillReference(first_skill)
            return
        self.app._set_status("No skill available to copy")

    @Slot()
    def copySelectedSkillsToClipboard(self):
        """Copies selected skill references for the current project to clipboard."""
        from skill_manager.core.quick_copy import format_project_skill_reference

        paths = self.app.skillModel.getFilteredSelectedPaths()
        if not paths:
            self.app._set_status("No skills selected")
            return

        references = []
        for path in paths:
            skill = next(
                (s for s in self.app.skillModel._all_filtered_skills if s.local_path == path), None
            )
            if skill:
                references.append(
                    format_project_skill_reference(
                        skill, self.app._client_format, all_skills=self.app.skillModel._all_skills
                    )
                )
            else:
                references.append(path)

        content = " ".join(references)
        self.app._clipboard.setText(content)
        self.app._set_status(f"Copied {len(references)} skills to clipboard")
        self._maybeMinimizeOnCopy()

    @Slot(str)
    def copyTextToClipboard(self, content: str):
        """Copies raw text to system clipboard."""
        self.app._clipboard.setText(str(content))
        self.app._set_status("Copied to clipboard")
        self._maybeMinimizeOnCopy()

    @Slot(dict, str)
    def copySkillReference(self, skill: dict, arg: str = ""):
        """Copies a formatted skill reference to clipboard."""
        from skill_manager.core.quick_copy import format_project_skill_reference

        ref = format_project_skill_reference(
            skill, self.app._client_format, all_skills=self.app.skillModel._all_skills
        )
        if arg:
            ref += f"({arg})"
        self.app._clipboard.setText(ref)
        self.app._set_status(f"Copied reference: {ref}")
        self._maybeMinimizeOnCopy()

    @Slot(str)
    def copyCollectionToClipboard(self, name: str):
        """Copies a collection's skill references to clipboard and auto-pastes."""
        from skill_manager.core.quick_copy import format_project_skill_reference

        entry = self.app._custom_collections.get(name, {})
        if not isinstance(entry, dict):
            return

        paths = entry.get("paths", [])
        if not paths:
            self.app._set_status(f"Collection '{name}' has no skills")
            return

        references = []
        for path in paths:
            skill = next((s for s in self.app.skillModel._all_skills if s.local_path == path), None)
            if skill:
                references.append(
                    format_project_skill_reference(
                        skill,
                        self.app._client_format,
                        all_skills=self.app.skillModel._all_skills,
                    )
                )
            else:
                references.append(path)

        content = " ".join(references)
        self.app._clipboard.setText(content)
        self.app._set_status(f"Copied collection '{name}' ({len(references)} skills)")

        # Auto-paste after a short delay to allow focus to settle
        delay = 120 if self.app.config_controller.autoMinimizeOnQuickCopy else 50
        if self.app.config_controller.autoMinimizeOnQuickCopy:
            self.minimizeAppRequested.emit()
        QTimer.singleShot(delay, self._send_paste_to_focused_window)

    def _send_paste_to_focused_window(self):
        """Helper that sends Ctrl+V to the focused window.

        Dispatches to the platform-appropriate implementation:
        Win32 keybd_event on Windows, wl-clipboard/ydotool on Linux.
        """
        import sys as _sys

        if _sys.platform == "win32":
            from skill_manager.utils.win32 import send_paste_to_focused_window as _paste
        else:
            from skill_manager.utils.linux import send_paste_to_focused_window as _paste

        if not _paste():
            self.app._set_status("Copied, but could not paste automatically")
