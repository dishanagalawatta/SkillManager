"""
Purpose: Abstract base class for sub-controllers to share state and access the AppController Hub.
Usage: Inherit from BaseController and access self.app or self.config.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from skill_manager.app import AppController
    from skill_manager.core.config import ConfigManager


class BaseController:
    """Base class for all sub-controllers."""

    def __init__(self, app: "AppController"):
        self.app = app
        self.config: ConfigManager = app._config
