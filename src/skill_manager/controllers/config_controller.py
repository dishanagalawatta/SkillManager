"""
Purpose: Manages skill sources, projects, and configuration state.
Usage: Accessed via AppController.config_mgr
"""

from PySide6.QtCore import Signal

from skill_manager.controllers.base import BaseController
from skill_manager.controllers.config.collection_shortcuts import CollectionShortcutsMixin
from skill_manager.controllers.config.collections import CollectionsMixin
from skill_manager.controllers.config.diagnostics import DiagnosticsMixin
from skill_manager.controllers.config.projects import ProjectsMixin
from skill_manager.controllers.config.settings import SettingsMixin
from skill_manager.controllers.config.shortcuts import ShortcutsMixin
from skill_manager.controllers.config.sources import SourcesMixin


class ConfigController(
    SettingsMixin,
    SourcesMixin,
    ProjectsMixin,
    ShortcutsMixin,
    CollectionsMixin,
    CollectionShortcutsMixin,
    DiagnosticsMixin,
    BaseController,
):
    """Controller for project configuration and sources.

    Uses Pydantic (AppConfig) for strict validation of configuration updates.

    Facade class: validated setting properties live in ``SettingsMixin``,
    source management in ``SourcesMixin``, project CRUD/labels in
    ``ProjectsMixin``, shortcut properties in ``ShortcutsMixin``, custom
    collections in ``CollectionsMixin``, per-collection shortcuts in
    ``CollectionShortcutsMixin``, and cache/diagnostic slots in
    ``DiagnosticsMixin`` — composed before ``BaseController`` so their
    slots/properties/signals register on this class. All ``*Changed``
    signals are re-declared here as the canonical class attributes.
    """

    shortcutsChanged = Signal()
    isRecordingShortcutChanged = Signal()
    updateProjectsChanged = Signal()
    clientFormatsChanged = Signal()
    customCollectionsChanged = Signal()
    scrollSpeedMultiplierChanged = Signal()
    skillPackageAutoUpdateModeChanged = Signal()
    autoMinimizeOnSnapChanged = Signal()
    autoMinimizeOnQuickCopyChanged = Signal()
    autoSelectSnapInQuickCopyChanged = Signal()
    autoCopySnapClientFormatChanged = Signal()
    temporarySnapsChanged = Signal()
    diagnosticLoggingChanged = Signal()

    # Cached property values (invalidated via _invalidate_project_cache)
    _cached_update_projects: list[dict] | None = None
    _cached_project_labels: list[str] | None = None
