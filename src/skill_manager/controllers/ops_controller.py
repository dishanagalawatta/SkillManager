"""
Purpose: Manages skill operations like copying, deleting, and status toggles.
Usage: Accessed via AppController.ops

Facade class: all implementation lives in the ``ops`` package mixins.
"""

from PySide6.QtCore import Signal

from skill_manager.controllers.base import BaseController
from skill_manager.controllers.ops.clipboard import ClipboardMixin
from skill_manager.controllers.ops.commands import CommandsMixin
from skill_manager.controllers.ops.copy import CopyMixin
from skill_manager.controllers.ops.delete import DeleteMixin
from skill_manager.controllers.ops.inspector import InspectorMixin
from skill_manager.controllers.ops.sync import SyncMixin
from skill_manager.controllers.ops.toggles import TogglesMixin


class OpsController(
    TogglesMixin,
    DeleteMixin,
    CopyMixin,
    ClipboardMixin,
    CommandsMixin,
    InspectorMixin,
    SyncMixin,
    BaseController,
):
    """Controller for skill-related operations."""

    minimizeAppRequested = Signal()
    commandSkillsCarryPrompt = Signal(str, str, str)
    commandPendingRemovals = Signal(str, list)

    _pending_command_update: dict | None = None

    def __init__(self, app):
        super().__init__(app)
        self._is_deleting = False
