"""Clipboard operations for the OpsController."""

import logging

from PySide6.QtCore import Slot

from skill_manager.controllers.ops._helpers import QTimer, _get_item_attr
from skill_manager.core.diagnostics import get_diagnostic_logger

logger = logging.getLogger(__name__)


class ClipboardMixin:
    """Copy skill references/text to the system clipboard.

    All writes go through :meth:`_write_clipboard`, which delegates to the
    app's :class:`~skill_manager.utils.clipboard_service.ClipboardService`
    (verified Qt write with native fallback) and only reports success when
    the write actually landed.
    """

    def _maybeMinimizeOnCopy(self):
        """Requests app minimization if the setting is enabled and current view is QuickCopy."""
        if (
            self.app.config_controller.autoMinimizeOnQuickCopy
            and self.app.ui_controller.currentView == "QuickCopy"
        ):
            self.minimizeAppRequested.emit()
            logger.info("Auto-minimize on Quick Copy triggered.")

    def _write_clipboard(self, content: str) -> bool:
        """Write *content* to the clipboard via the ClipboardService.

        Returns ``True`` only when the write was verified or a native
        fallback succeeded.
        """
        service = getattr(self.app, "clipboard_service", None)
        if service is not None:
            return bool(service.copy_text(content))
        qt = getattr(self.app, "_clipboard", None)
        if qt is not None:
            qt.setText(content)
            return True
        logger.error("No clipboard backend available on AppController")
        return False

    def _flush_incubation_if_needed(self):
        """Ensure incubation is ended and pending model signals are replayed before clipboard operations."""
        model = getattr(self.app, "skillModel", None)
        if model is not None and getattr(model, "_incubating", False):
            if hasattr(model, "_force_end_incubation"):
                model._force_end_incubation()
            if hasattr(model, "onIncubationReady"):
                model.onIncubationReady()

    def _get_active_model(self):
        """Return the model corresponding to the active view (QuickCopy vs Library)."""
        if (
            hasattr(self.app, "ui_controller")
            and getattr(self.app.ui_controller, "currentView", "") == "QuickCopy"
            and hasattr(self.app, "quickCopyModel")
        ):
            return self.app.quickCopyModel
        return getattr(self.app, "skillModel", None)

    def _find_skill_by_path(self, path: str):
        """Locate skill entity across all_filtered_skills, all_skills, or discovery state."""
        self._flush_incubation_if_needed()
        for model_attr in ("_quick_copy_model", "_library_model", "quickCopyModel", "skillModel"):
            model = getattr(self.app, model_attr, None)
            if model is not None:
                filtered = getattr(model, "_all_filtered_skills", [])
                for s in filtered:
                    if _get_item_attr(s, "local_path") == path:
                        return s
                all_skills = getattr(model, "_all_skills", [])
                for s in all_skills:
                    if _get_item_attr(s, "local_path") == path:
                        return s

        dc = getattr(self.app, "discovery_controller", None)
        if dc is not None:
            state = getattr(dc, "_last_prepared_state", None)
            if state is not None:
                for s in getattr(state, "all_skills", []):
                    if _get_item_attr(s, "local_path") == path:
                        return s
        return None

    def _safe_format_reference(self, skill, fallback: str) -> str:
        """Format a skill reference; a malformed skill must never abort the copy."""
        self._flush_incubation_if_needed()
        from skill_manager.core.quick_copy import format_project_skill_reference

        try:
            return format_project_skill_reference(
                skill,
                self.app._client_format,
                all_skills=getattr(self.app.skillModel, "_all_skills", []),
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to format skill reference for %r: %s", fallback, exc)
            get_diagnostic_logger().log_event(
                "WARNING",
                "clipboard",
                f"format reference failed for {fallback}: {exc}",
            )
            return fallback

    @Slot(str)
    def copySkillToClipboard(self, path: str):
        """Finds skill by path and copies its reference to clipboard."""
        skill = self._find_skill_by_path(path)
        if skill:
            self.copySkillReference(skill)  # type: ignore[arg-type]
        else:
            self.copyTextToClipboard(path)

    def _get_model_selected_count(self, model) -> int:
        """Safely retrieve the selected count of a model."""
        if model is None:
            return 0
        cnt = getattr(model, "selectedCount", 0)
        if isinstance(cnt, (int, float)):
            return int(cnt)
        return 0

    @Slot()
    def copyCurrentSelectionOrFocusedSkill(self):
        """Orchestrates copying based on selection or focus."""
        self._flush_incubation_if_needed()
        model = self._get_active_model()
        if self._get_model_selected_count(model) > 0:
            self.copySelectedSkillsToClipboard()
            return
        if self._get_model_selected_count(getattr(self.app, "quickCopyModel", None)) > 0:
            self.copySelectedSkillsToClipboard()
            return
        if self._get_model_selected_count(getattr(self.app, "skillModel", None)) > 0:
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
                "is_snap": selected.is_snap,
            }
            self.copySkillReference(data)
            return
        first_skill = model.get_skill_at(0) if model is not None else None
        if not first_skill and hasattr(self.app, "skillModel"):
            first_skill = self.app.skillModel.get_skill_at(0)
        if first_skill:
            self.copySkillReference(first_skill)
            return
        self.app._set_status("No skill available to copy")

    @Slot()
    def copySelectedSkillsToClipboard(self):
        """Copies selected skill references for the current project to clipboard."""
        self._flush_incubation_if_needed()
        model = self._get_active_model()
        raw_paths = model.getFilteredSelectedPaths() if model is not None else []
        paths = list(raw_paths) if isinstance(raw_paths, (list, tuple, set)) else []
        if not paths and model is not getattr(self.app, "quickCopyModel", None):
            qc_model = getattr(self.app, "quickCopyModel", None)
            if qc_model is not None:
                qc_paths = qc_model.getFilteredSelectedPaths()
                if isinstance(qc_paths, (list, tuple, set)) and qc_paths:
                    paths = list(qc_paths)
        if not paths and model is not getattr(self.app, "skillModel", None):
            sm_model = getattr(self.app, "skillModel", None)
            if sm_model is not None:
                sm_paths = sm_model.getFilteredSelectedPaths()
                if isinstance(sm_paths, (list, tuple, set)) and sm_paths:
                    paths = list(sm_paths)

        if not paths:
            self.app._set_status("No skills selected")
            return

        references = []
        for path in paths:
            skill = self._find_skill_by_path(path)
            if skill:
                references.append(self._safe_format_reference(skill, path))
            else:
                references.append(path)

        content = " ".join(references)
        if self._write_clipboard(content):
            self.app._set_status(f"Copied {len(references)} skills to clipboard")
            self._maybeMinimizeOnCopy()
        else:
            self.app._set_status("Copy failed — clipboard unavailable")

    @Slot(str)
    def copyTextToClipboard(self, content: str):
        """Copies raw text to system clipboard."""
        self._flush_incubation_if_needed()
        if self._write_clipboard(str(content)):
            self.app._set_status("Copied to clipboard")
            self._maybeMinimizeOnCopy()
        else:
            self.app._set_status("Copy failed — clipboard unavailable")

    @Slot(dict, str)
    def copySkillReference(self, skill: dict, arg: str = ""):
        """Copies a formatted skill reference to clipboard."""
        self._flush_incubation_if_needed()
        ref = self._safe_format_reference(skill, _get_item_attr(skill, "local_path"))
        if arg:
            ref += f"({arg})"
        if self._write_clipboard(ref):
            self.app._set_status(f"Copied reference: {ref}")
            self._maybeMinimizeOnCopy()
        else:
            self.app._set_status("Copy failed — clipboard unavailable")

    @Slot(str)
    def copyCollectionToClipboard(self, name: str):
        """Copies a collection's skill references to clipboard and auto-pastes."""
        self._flush_incubation_if_needed()
        entry = self.app._custom_collections.get(name, {})
        if not isinstance(entry, dict):
            return

        paths = entry.get("paths", [])
        if not paths:
            self.app._set_status(f"Collection '{name}' has no skills")
            return

        references = []
        for path in paths:
            skill = self._find_skill_by_path(path)
            if skill:
                references.append(self._safe_format_reference(skill, path))
            else:
                references.append(path)

        content = " ".join(references)
        if not self._write_clipboard(content):
            self.app._set_status("Copy failed — clipboard unavailable")
            return
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
            from skill_manager.utils.linux import (
                send_paste_to_focused_window as _paste,
                ydotool_daemon_health,
            )

        if _paste():
            return
        if _sys.platform != "win32":
            health = ydotool_daemon_health()
            if health == "not-installed":
                self.app._set_status(
                    "Copied, but could not paste automatically — ydotool is not installed"
                )
                return
            if health == "daemon-down":
                self.app._set_status(
                    "Copied, but could not paste automatically — ydotool daemon "
                    "(ydotoold) is not running"
                )
                return
        self.app._set_status("Copied, but could not paste automatically")
