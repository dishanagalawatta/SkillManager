"""
SelectedSkillController — live-bound QObject replacing QQmlPropertyMap.

Instead of storing a stale snapshot in a QQmlPropertyMap and manually
patching it on ``structureMutated``, this controller:

1. Exposes every skill field as a proper ``Q_PROPERTY`` so QML bindings
   get individual change-notification (no overlay flash).
2. Subscribes to the model's ``dataChanged`` signal so incremental
   updates (e.g. body_content loaded by discovery, is_starred toggled
   by the user) propagate automatically — no manual refresh chain.
3. Eliminates the ``self.sender()`` fragility from the old handler.

Usage
-----
    ctrl = SelectedSkillController(app)
    ctrl.setSelection({"local_path": "…", "name": "…", "body_content": "…", …})
    ctrl.clearSelection()
"""

from __future__ import annotations

import dataclasses
import logging
import os
from typing import TYPE_CHECKING, Any

from PySide6.QtCore import Property, QModelIndex, QObject, QPersistentModelIndex, Signal

if TYPE_CHECKING:
    from skill_manager.app import AppController
    from skill_manager.core.models.qt_model import SkillModel

logger = logging.getLogger(__name__)


def resolve_skill_file_path(path: str) -> str | None:
    """Resolve a local path (file or directory) to an actual readable markdown file path."""
    if not path:
        return None
    if os.path.isfile(path):
        return path
    if os.path.isdir(path):
        for candidate_name in ("SKILL.md", "skill.md", "README.md"):
            cand = os.path.join(path, candidate_name)
            if os.path.isfile(cand):
                return cand
        try:
            for entry in os.listdir(path):
                if entry.endswith(".md"):
                    cand = os.path.join(path, entry)
                    if os.path.isfile(cand):
                        return cand
        except Exception:
            pass
    return None


class SelectedSkillController(QObject):
    """Live-bound QObject that holds the currently-selected skill's fields.

    QML accesses each field via a named ``Q_PROPERTY`` (e.g.
    ``selectedSkillController.name``, ``selectedSkillController.bodyContent``).
    Every field has its own ``XxxChanged`` signal so QML nested bindings
    re-evaluate only the properties that actually changed.
    """

    # ── Per-field change signals ──────────────────────────────────
    nameChanged = Signal()
    bodyContentChanged = Signal()
    descriptionChanged = Signal()
    localPathChanged = Signal()
    isCommandChanged = Signal()
    isScreenshotChanged = Signal()
    isStarredChanged = Signal()
    isArchivedChanged = Signal()
    categoryChanged = Signal()
    riskChanged = Signal()
    sourceChanged = Signal()
    dateChanged = Signal()
    projectLabelChanged = Signal()
    rawContentChanged = Signal()

    # ── Combined signal — fires whenever any field changes.
    #    Useful for coarse-grained observers (e.g. the overlay toggle).
    selectedSkillChanged = Signal()

    def __init__(self, app: AppController) -> None:
        super().__init__()
        self._app = app

        # Internal storage for each Q_PROPERTY — initialise to empty.
        self._name: str = ""
        self._body_content: str = ""
        self._description: str = ""
        self._local_path: str = ""
        self._is_command: bool = False
        self._is_screenshot: bool = False
        self._is_starred: bool = False
        self._is_archived: bool = False
        self._category: str = ""
        self._risk: str = ""
        self._source: str = ""
        self._date: str = ""
        self._project_label: str = ""
        self._raw_content: str = ""

        # ── Subscribe to incremental data changes on both models ──
        lib: SkillModel = app._library_model
        qc: SkillModel = app._quick_copy_model
        lib.dataChanged.connect(self._on_data_changed)
        qc.dataChanged.connect(self._on_data_changed)

        # Also listen for model resets (beginResetModel/endResetModel).
        # After a reset the model's data() is fresh, so we re-read our path.
        lib.modelReset.connect(self._on_model_reset)
        qc.modelReset.connect(self._on_model_reset)

    # ── Q_PROPERTY definitions ────────────────────────────────────
    # (snake_case method name → camelCase QML property name;
    #  PySide6 maps ``def body_content`` → ``bodyContent``)

    @Property(str, notify=nameChanged)
    def name(self) -> str:
        return self._name

    @name.setter  # type: ignore[no-redef]
    def name(self, value: str) -> None:
        if self._name != value:
            self._name = value
            self.nameChanged.emit()

    @Property(str, notify=bodyContentChanged)
    def body_content(self) -> str:
        return self._body_content

    @body_content.setter
    def body_content(self, value: str) -> None:
        if self._body_content != value:
            self._body_content = value
            self.bodyContentChanged.emit()

    @Property(str, notify=descriptionChanged)
    def description(self) -> str:
        return self._description

    @description.setter
    def description(self, value: str) -> None:
        if self._description != value:
            self._description = value
            self.descriptionChanged.emit()

    @Property(str, notify=localPathChanged)
    def local_path(self) -> str:
        return self._local_path

    @local_path.setter
    def local_path(self, value: str) -> None:
        if self._local_path != value:
            self._local_path = value
            self.localPathChanged.emit()

    @Property(bool, notify=isCommandChanged)
    def is_command(self) -> bool:
        return self._is_command

    @is_command.setter
    def is_command(self, value: bool) -> None:
        if self._is_command != value:
            self._is_command = value
            self.isCommandChanged.emit()

    @Property(bool, notify=isScreenshotChanged)
    def is_screenshot(self) -> bool:
        return self._is_screenshot

    @is_screenshot.setter
    def is_screenshot(self, value: bool) -> None:
        if self._is_screenshot != value:
            self._is_screenshot = value
            self.isScreenshotChanged.emit()

    @Property(bool, notify=isStarredChanged)
    def is_starred(self) -> bool:
        return self._is_starred

    @is_starred.setter
    def is_starred(self, value: bool) -> None:
        if self._is_starred != value:
            self._is_starred = value
            self.isStarredChanged.emit()

    @Property(bool, notify=isArchivedChanged)
    def is_archived(self) -> bool:
        return self._is_archived

    @is_archived.setter
    def is_archived(self, value: bool) -> None:
        if self._is_archived != value:
            self._is_archived = value
            self.isArchivedChanged.emit()

    @Property(str, notify=categoryChanged)
    def category(self) -> str:
        return self._category

    @category.setter
    def category(self, value: str) -> None:
        if self._category != value:
            self._category = value
            self.categoryChanged.emit()

    @Property(str, notify=riskChanged)
    def risk(self) -> str:
        return self._risk

    @risk.setter
    def risk(self, value: str) -> None:
        if self._risk != value:
            self._risk = value
            self.riskChanged.emit()

    @Property(str, notify=sourceChanged)
    def source(self) -> str:
        return self._source

    @source.setter
    def source(self, value: str) -> None:
        if self._source != value:
            self._source = value
            self.sourceChanged.emit()

    @Property(str, notify=dateChanged)
    def date(self) -> str:
        return self._date

    @date.setter
    def date(self, value: str) -> None:
        if self._date != value:
            self._date = value
            self.dateChanged.emit()

    @Property(str, notify=projectLabelChanged)
    def project_label(self) -> str:
        return self._project_label

    @project_label.setter
    def project_label(self, value: str) -> None:
        if self._project_label != value:
            self._project_label = value
            self.projectLabelChanged.emit()

    @Property(str, notify=rawContentChanged)
    def raw_content(self) -> str:
        return self._raw_content

    @raw_content.setter
    def raw_content(self, value: str) -> None:
        if self._raw_content != value:
            self._raw_content = value
            self.rawContentChanged.emit()

    # ── Public API ────────────────────────────────────────────────

    def setSelection(self, skill_dict: dict[str, Any]) -> None:
        """Populate all fields from a skill dictionary.

        Called by ``UIController.selectSkill()`` (and other callers that
        previously used ``set_selected_skill``).
        """
        path = skill_dict.get("local_path", "")
        file_path = resolve_skill_file_path(path)
        if file_path and not skill_dict.get("body_content") and not skill_dict.get("raw_content"):
            try:
                from skill_manager.core.parsing.skill import parse_skill_md

                parsed = parse_skill_md(file_path)
                if parsed.get("body_content") or parsed.get("raw_content"):
                    skill_dict = dict(skill_dict)
                    if parsed.get("body_content"):
                        skill_dict["body_content"] = parsed["body_content"]
                    if parsed.get("raw_content"):
                        skill_dict["raw_content"] = parsed["raw_content"]
            except Exception as exc:
                logger.warning("Failed to auto-read skill file for %s: %s", file_path, exc)

        self._path = path
        self._update_from_dict(skill_dict)
        self.selectedSkillChanged.emit()

        bc = skill_dict.get("body_content", "")
        bc_preview = bc[:80] if bc else "(empty)"
        logger.info(
            "[DIAG] SelectedSkillController.setSelection path=%s body_len=%d body_preview=%r",
            self._path,
            len(bc),
            bc_preview,
        )

    def clearSelection(self) -> None:
        """Reset all fields to empty/default values."""
        self._path = ""
        self._update_from_dict({})
        self.selectedSkillChanged.emit()

    # ── Internal helpers ──────────────────────────────────────────

    def _update_from_dict(self, d: dict[str, Any]) -> None:
        """Set each internal field from ``d``, emitting per-field signals.

        Uses direct attribute writes so the setter fires the right signal.
        """
        self.name = d.get("name", "")
        self.body_content = d.get("body_content", "")
        self.description = d.get("description", "")
        self.local_path = d.get("local_path", "")
        self.is_command = bool(d.get("is_command", False))
        self.is_screenshot = bool(d.get("is_screenshot", False))
        self.is_starred = bool(d.get("is_starred", False))
        self.is_archived = bool(d.get("is_archived", False))
        self.category = d.get("category", "")
        self.risk = d.get("risk", "")
        self.source = d.get("source", "")
        self.date = d.get("date", "")
        self.project_label = d.get("project_label", "")
        self.raw_content = d.get("raw_content", "")

    def _skill_for_path(self, model: Any, path: str) -> dict[str, Any] | None:
        """Look up a skill by ``local_path`` in *model* and return a dict."""
        if not path:
            return None
        skill_obj = model.find_by_path(path)
        if skill_obj is None:
            resolved = resolve_skill_file_path(path)
            if resolved:
                skill_obj = model.find_by_path(resolved)
        if skill_obj is not None:
            return dataclasses.asdict(skill_obj)
        return None

    def _on_data_changed(
        self,
        top_left: QModelIndex | QPersistentModelIndex,
        bottom_right: QModelIndex | QPersistentModelIndex,
        roles: list[int],
    ) -> None:
        """React to model ``dataChanged`` — refresh if our skill was updated.

        Only re-reads fields that the model reports as changed (``roles``).
        If ``roles`` is empty (meaning "everything changed") we refresh all
        fields.
        """
        if not self._local_path:
            return

        model: SkillModel = self.sender()  # type: ignore[assignment]
        if model is None:
            return

        # Check whether our selected skill is in the changed row range.
        found = False
        for row in range(top_left.row(), bottom_right.row() + 1):
            idx = model.index(row, 0)
            path: str = idx.data(model.PathRole) or ""
            if path == self._local_path:
                found = True
                break

        if not found:
            return

        # ── Re-read fields ────────────────────────────────────────
        # If roles is empty → ALL roles changed.  Otherwise only the
        # listed roles changed.
        roles_set = set(roles) if roles else set(model._ALL_ROLES)

        if not roles_set or model.BodyContentRole in roles_set:
            self.body_content = str(idx.data(model.BodyContentRole) or "")
        if not roles_set or model.DescriptionRole in roles_set:
            self.description = str(idx.data(model.DescriptionRole) or "")
        if not roles_set or model.NameRole in roles_set:
            self.name = str(idx.data(model.NameRole) or "")
        if not roles_set or model.IsStarredRole in roles_set:
            self.is_starred = bool(idx.data(model.IsStarredRole))
        if not roles_set or model.IsCommandRole in roles_set:
            self.is_command = bool(idx.data(model.IsCommandRole))
        if not roles_set or model.IsScreenshotRole in roles_set:
            self.is_screenshot = bool(idx.data(model.IsScreenshotRole))
        if not roles_set or model.IsArchivedRole in roles_set:
            self.is_archived = bool(idx.data(model.IsArchivedRole))
        if not roles_set or model.CategoryRole in roles_set:
            self.category = str(idx.data(model.CategoryRole) or "")
        if not roles_set or model.RiskRole in roles_set:
            self.risk = str(idx.data(model.RiskRole) or "")
        if not roles_set or model.SourceRole in roles_set:
            self.source = str(idx.data(model.SourceRole) or "")
        if not roles_set or model.DateRole in roles_set:
            self.date = str(idx.data(model.DateRole) or "")
        if not roles_set or model.ProjectRole in roles_set:
            self.project_label = str(idx.data(model.ProjectRole) or "")
        if not roles_set or model.RawContentRole in roles_set:
            self.raw_content = str(idx.data(model.RawContentRole) or "")

        logger.debug(
            "[SelectedSkillController] refreshed fields from dataChanged roles=%s path=%s",
            roles,
            self._path,
        )

    def _on_model_reset(self) -> None:
        """After a full model reset, re-read the selected skill from the sender.

        The ``modelReset`` signal fires after ``endResetModel()``, at which
        point the model's ``data()`` is fresh.  This handles the case where
        ``replacePreparedState`` did a full reset and the old selected-skill
        data became stale.
        """
        if not self._local_path:
            return

        model: SkillModel = self.sender()  # type: ignore[assignment]
        if model is None:
            return

        d = self._skill_for_path(model, self._local_path)
        if d is not None:
            logger.info(
                "[SelectedSkillController] reset refresh path=%s body_len=%d",
                self._local_path,
                len(d.get("body_content", "") or ""),
            )
            self._update_from_dict(d)
            self.selectedSkillChanged.emit()
