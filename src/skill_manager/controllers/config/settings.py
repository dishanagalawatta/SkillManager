"""Validated setting properties for the ConfigController facade.

``_set_config_value`` validates against ``AppConfig`` before persisting;
every property here is a ``@Property`` with a ``*Changed`` notify signal
that is re-declared on the facade class.
"""

import logging
from typing import Any

from PySide6.QtCore import Property, Signal, SignalInstance

from skill_manager.core.diagnostics import get_diagnostic_logger
from skill_manager.core.schemas import AppConfig

logger = logging.getLogger(__name__)


class SettingsMixin:
    """Validated, AppConfig-checked setting properties.

    The ``*Changed`` signals are re-declared here so the
    ``@Property(notify=...)`` decorators can reference them at class
    definition time; the facade class re-declares the same signals as
    its own class attributes (the canonical QML-visible instances).
    """

    scrollSpeedMultiplierChanged = Signal()
    skillPackageAutoUpdateModeChanged = Signal()
    autoMinimizeOnScreenshotChanged = Signal()
    autoMinimizeOnQuickCopyChanged = Signal()
    autoSelectScreenshotInQuickCopyChanged = Signal()
    autoCopyScreenshotClientFormatChanged = Signal()
    temporaryScreenshotsChanged = Signal()
    diagnosticLoggingChanged = Signal()

    def _set_config_value(self, key: str, value: Any, signal: SignalInstance | None = None):
        """Unified setter that validates against AppConfig before persisting."""
        try:
            # Create a partial config to validate this specific key
            validated = AppConfig.model_validate({key: value})
            final_value = getattr(validated, key)

            if self.config.get(key) != final_value:
                self.config.set(key, final_value)
                if signal:
                    signal.emit()
                return True
        except Exception as e:
            logger.warning("[CONFIG] Validation failed for %s=%s: %s", key, value, e)
        return False

    @Property(float, notify=scrollSpeedMultiplierChanged)
    def scrollSpeedMultiplier(self):  # type: ignore[reportRedeclaration]
        return self.config.get("scroll_speed_multiplier", 1.0)

    @scrollSpeedMultiplier.setter  # type: ignore[func-attr]
    def scrollSpeedMultiplier(self, value):
        self._set_config_value("scroll_speed_multiplier", value, self.scrollSpeedMultiplierChanged)

    @Property(str, notify=skillPackageAutoUpdateModeChanged)
    def skillPackageAutoUpdateMode(self):  # type: ignore[reportRedeclaration]
        return self.config.get("skill_package_auto_update_mode", "prompt")

    @skillPackageAutoUpdateMode.setter  # type: ignore[func-attr]
    def skillPackageAutoUpdateMode(self, value):
        self._set_config_value(
            "skill_package_auto_update_mode", value, self.skillPackageAutoUpdateModeChanged
        )

    @Property(bool, notify=autoMinimizeOnScreenshotChanged)
    def autoMinimizeOnScreenshot(self):  # type: ignore[reportRedeclaration]
        return self.config.get("auto_minimize_on_screenshot", False)

    @autoMinimizeOnScreenshot.setter  # type: ignore[func-attr]
    def autoMinimizeOnScreenshot(self, value):
        self._set_config_value(
            "auto_minimize_on_screenshot", value, self.autoMinimizeOnScreenshotChanged
        )

    @Property(bool, notify=autoMinimizeOnQuickCopyChanged)
    def autoMinimizeOnQuickCopy(self):  # type: ignore[reportRedeclaration]
        return self.config.get("auto_minimize_on_quick_copy", False)

    @autoMinimizeOnQuickCopy.setter  # type: ignore[func-attr]
    def autoMinimizeOnQuickCopy(self, value):
        self._set_config_value(
            "auto_minimize_on_quick_copy", value, self.autoMinimizeOnQuickCopyChanged
        )

    @Property(bool, notify=autoSelectScreenshotInQuickCopyChanged)
    def autoSelectScreenshotInQuickCopy(self):  # type: ignore[reportRedeclaration]
        return self.config.get("auto_select_screenshot_in_quick_copy", False)

    @autoSelectScreenshotInQuickCopy.setter  # type: ignore[func-attr]
    def autoSelectScreenshotInQuickCopy(self, value):
        self._set_config_value(
            "auto_select_screenshot_in_quick_copy",
            value,
            self.autoSelectScreenshotInQuickCopyChanged,
        )

    @Property(bool, notify=autoCopyScreenshotClientFormatChanged)
    def autoCopyScreenshotClientFormat(self):  # type: ignore[reportRedeclaration]
        return self.config.get("auto_copy_screenshot_client_format", False)

    @autoCopyScreenshotClientFormat.setter  # type: ignore[func-attr]
    def autoCopyScreenshotClientFormat(self, value):
        self._set_config_value(
            "auto_copy_screenshot_client_format",
            value,
            self.autoCopyScreenshotClientFormatChanged,
        )

    @Property(bool, notify=temporaryScreenshotsChanged)
    def temporaryScreenshots(self):  # type: ignore[reportRedeclaration]
        return self.config.get("temporary_screenshots", False)

    @temporaryScreenshots.setter  # type: ignore[func-attr]
    def temporaryScreenshots(self, value):
        self._set_config_value("temporary_screenshots", value, self.temporaryScreenshotsChanged)

    @Property(bool, notify=diagnosticLoggingChanged)
    def diagnosticLogging(self):  # type: ignore[reportRedeclaration]
        return self.config.get("diagnostic_logging", False)

    @diagnosticLogging.setter  # type: ignore[func-attr]
    def diagnosticLogging(self, value):
        if self._set_config_value("diagnostic_logging", value, self.diagnosticLoggingChanged):
            # Apply immediately at runtime — no restart required
            get_diagnostic_logger().set_enabled(value)
