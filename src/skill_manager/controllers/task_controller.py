"""Per-project task list controller.

Exposes the task list of the active project to QML and keeps the persisted
state in sync. The Quick Copy view uses it to render the collapsible
"Tasks" panel next to the skill list.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from PySide6.QtCore import Property, QObject, Signal, Slot

from skill_manager.core import tasks as task_store
from skill_manager.core.quick_copy import format_project_skill_reference

logger = logging.getLogger(__name__)


class TaskController(QObject):
    """Manages the per-project task lists."""

    tasksChanged = Signal()

    def __init__(self, app):
        super().__init__()
        self.app = app

    # ── Helpers ──────────────────────────────────────────────────────

    def _project_path(self, project_path: str = "") -> str:
        """Resolve the project a task operation targets.

        An empty *project_path* means "the active project".
        """
        if project_path:
            return project_path
        label = getattr(self.app, "_current_project_label", "") or ""
        if not label:
            return ""
        return self._path_for_label(label)

    def _path_for_label(self, label: str) -> str:
        """Map a project label back to its path.

        The app's own label→path mapping is authoritative (it knows the
        aliases); the canonical-key comparison is the fallback.
        """
        config_controller = getattr(self.app, "config_controller", None)
        getter = getattr(config_controller, "getProjectPath", None)
        if callable(getter):
            try:
                path = getter(label)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Task controller: getProjectPath(%r) failed: %s", label, exc)
                path = ""
            if isinstance(path, str) and path:
                return path

        from skill_manager.core.quick_copy import project_label

        for candidate in list(self.app._projects or []):
            try:
                if project_label(Path(candidate)) == label:
                    return str(candidate)
            except Exception:  # noqa: BLE001
                continue
        return ""

    def _active_project_path(self) -> str:
        return self._project_path("")

    def _emit(self) -> None:
        self.tasksChanged.emit()

    # ── Properties ───────────────────────────────────────────────────

    @Property("QVariantList", notify=tasksChanged)
    def currentProjectTasks(self) -> list[dict[str, Any]]:
        """The task list of the active project."""
        path = self._active_project_path()
        if not path:
            return []
        return task_store.records_to_dicts(task_store.get_tasks(path))

    @Property(int, notify=tasksChanged)
    def activeTaskCount(self) -> int:
        """Number of open tasks in the active project."""
        path = self._active_project_path()
        if not path:
            return 0
        active, _completed = task_store.counts_for_project(path)
        return active

    @Property(int, notify=tasksChanged)
    def completedTaskCount(self) -> int:
        """Number of completed tasks in the active project."""
        path = self._active_project_path()
        if not path:
            return 0
        _active, completed = task_store.counts_for_project(path)
        return completed

    @Property(int, notify=tasksChanged)
    def currentProjectTaskCount(self) -> int:
        """Total number of tasks (open + done) in the active project."""
        path = self._active_project_path()
        if not path:
            return 0
        return len(task_store.get_tasks(path))

    @Property(str, notify=tasksChanged)
    def activeProjectKey(self) -> str:
        """The canonical key of the active project (empty when none)."""
        path = self._active_project_path()
        return task_store.project_task_key(path) if path else ""

    @Property("QVariantMap", notify=tasksChanged)
    def projectTaskCounts(self) -> dict[str, int]:
        """Open task count per configured project path.

        Keyed by the project path exactly as the app stores it, so QML can
        look the count up with the path it already has. Projects without
        open tasks are omitted.
        """
        state = task_store.load_state()
        counts: dict[str, int] = {}
        for path in list(self.app._projects or []):
            key = task_store.project_task_key(path)
            records = state.projects.get(key, [])
            active = sum(1 for record in records if not record.completed)
            if active:
                counts[str(path)] = active
        return counts

    @Slot(str, result=int)
    def openTaskCountForProject(self, project_path: str) -> int:
        """Number of open tasks in *project_path* (used for the project badge)."""
        if not project_path:
            return 0
        active, _completed = task_store.counts_for_project(project_path)
        return active

    # ── Slots ────────────────────────────────────────────────────────

    @Slot(str, str, str, str, "QVariantList", result=bool)
    def addProjectTask(
        self,
        project_path: str,
        title: str,
        priority: str = "medium",
        description: str = "",
        attachments: list[str] | None = None,
    ) -> bool:
        """Add a task to *project_path* (empty path = the active project)."""
        path = self._project_path(project_path)
        if not path:
            self.app._set_status("Select a project before adding a task.")
            return False
        record = task_store.add_task(
            path,
            title,
            priority=priority,
            description=description,
            attachments=attachments,
        )
        if record is None:
            return False
        self._emit()
        return True

    @Slot(str, str, result=str)
    def attachTaskImage(self, project_path: str, source_url: str) -> str:
        """Copy an image file into the task attachment store.

        Returns the stored path, or ``""`` when the file is not an image
        (the composer then tells the user instead of silently dropping it).
        """
        path = self._project_path(project_path)
        if not path:
            return ""
        return task_store.store_attachment(path, source_url)

    @Slot(str, result=str)
    def attachClipboardImage(self, project_path: str) -> str:
        """Store an image currently on the clipboard (e.g. a screenshot)."""
        path = self._project_path(project_path)
        if not path:
            return ""
        try:
            from PySide6.QtCore import QBuffer, QByteArray
            from PySide6.QtGui import QGuiApplication

            clipboard = QGuiApplication.clipboard()
            image = clipboard.image() if clipboard is not None else None
            if image is None or image.isNull():
                return ""
            data = QByteArray()
            buffer = QBuffer(data)
            buffer.open(QBuffer.OpenModeFlag.WriteOnly)
            saved = image.save(buffer, "PNG")
            buffer.close()
            if not saved:
                return ""
            return task_store.store_attachment_bytes(path, bytes(data), ".png")
        except Exception as exc:  # noqa: BLE001
            logger.warning("Task controller: clipboard image unavailable: %s", exc)
            return ""

    @Slot(str, str, result=bool)
    def toggleProjectTask(self, project_path: str, task_id: str) -> bool:
        """Flip the completed flag of a task."""
        path = self._project_path(project_path)
        if not path:
            return False
        record = task_store.toggle_task(path, task_id)
        if record is None:
            return False
        self._emit()
        return True

    @Slot(str, str, str, str, str, result=bool)
    def updateProjectTask(
        self,
        project_path: str,
        task_id: str,
        title: str = "",
        description: str = "",
        priority: str = "",
    ) -> bool:
        """Update a task's title, description and priority."""
        path = self._project_path(project_path)
        if not path:
            return False
        record = task_store.update_task(
            path,
            task_id,
            title=title or None,
            description=description if description != "" else None,
            priority=priority or None,
        )
        if record is None:
            return False
        self._emit()
        return True

    @Slot(str, str, result=bool)
    def deleteProjectTask(self, project_path: str, task_id: str) -> bool:
        """Delete a task."""
        path = self._project_path(project_path)
        if not path:
            return False
        removed = task_store.delete_task(path, task_id)
        if removed:
            self._emit()
        return removed

    @Slot(str, result=int)
    def clearCompletedProjectTasks(self, project_path: str) -> int:
        """Remove every completed task of *project_path*."""
        path = self._project_path(project_path)
        if not path:
            return 0
        removed = task_store.clear_completed_tasks(path)
        if removed:
            self._emit()
        return removed

    @Slot(str, str, result=bool)
    def reorderProjectTasks(self, project_path: str, ordered_ids_json: str) -> bool:
        """Reorder the task list to match a JSON array of task ids."""
        import json

        path = self._project_path(project_path)
        if not path:
            return False
        try:
            ordered_ids = json.loads(ordered_ids_json or "[]")
        except Exception:
            return False
        if not isinstance(ordered_ids, list):
            return False
        changed = task_store.reorder_tasks(path, [str(i) for i in ordered_ids])
        if changed:
            self._emit()
        return changed

    @Slot(str, str, result=bool)
    def copyTaskAsPrompt(self, project_path: str, task_id: str) -> bool:
        """Copy a task (with its linked skill references) to the clipboard.

        The skill references are formatted for the client format that is
        currently selected in Quick Copy, so the pasted text is directly
        usable in the target agent.
        """
        path = self._project_path(project_path)
        if not path:
            return False

        record = None
        for candidate in task_store.get_tasks(path):
            if candidate.id == task_id:
                record = candidate
                break
        if record is None:
            return False

        client_format = getattr(self.app, "_client_format", "") or ""
        references = self._format_linked_skills(record.linked_skills, client_format)

        lines = [record.title]
        if record.description:
            lines.append(record.description)
        if record.attachments:
            lines.append("")
            lines.append("Attachments:")
            lines.extend(f"- {path}" for path in record.attachments)
        if references:
            lines.append("")
            lines.extend(references)
        text = "\n".join(lines).strip()

        try:
            self.app.clipboard_service.copy_text(text)
        except Exception as exc:
            logger.warning("Task controller: clipboard write failed: %s", exc)
            self.app._set_status("Could not copy the task to the clipboard.")
            return False

        self.app._set_status(f"Copied task: {record.title}")
        return True

    def _format_linked_skills(self, names: list[str], client_format: str) -> list[str]:
        """Render the linked skill names in the active client's syntax."""
        if not names:
            return []

        known = []
        for model_name in ("_library_model", "_quick_copy_model"):
            model = getattr(self.app, model_name, None)
            for skill in getattr(model, "_all_skills", []) or []:
                known.append(skill)

        by_name: dict[str, Any] = {}
        for skill in known:
            folder = str(getattr(skill, "folder_name", "") or "").lower()
            name = str(getattr(skill, "name", "") or "").lower()
            if folder:
                by_name.setdefault(folder, skill)
            if name:
                by_name.setdefault(name, skill)

        references: list[str] = []
        for raw in names:
            key = str(raw).strip().lower()
            skill = by_name.get(key)
            if skill is None:
                references.append(f"/{raw}")
                continue
            try:
                references.append(format_project_skill_reference(skill, client_format, known))
            except Exception as exc:
                logger.warning("Task controller: cannot format skill %r: %s", raw, exc)
                references.append(f"/{raw}")
        return references

    # ── Lifecycle ────────────────────────────────────────────────────

    def refresh(self) -> None:
        """Notify QML that the task lists changed."""
        self._emit()
