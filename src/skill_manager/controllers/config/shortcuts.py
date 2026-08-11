"""Keyboard shortcut properties and management for the ConfigController facade."""

from PySide6.QtCore import Property, Signal, Slot


class ShortcutsMixin:
    """Shortcut value/enabled properties plus get/set/reset operations.

    ``shortcutsChanged``/``isRecordingShortcutChanged`` are re-declared
    here for the ``@Property(notify=...)`` decorators; the facade class
    re-declares them as its canonical class attributes.
    """

    shortcutsChanged = Signal()
    isRecordingShortcutChanged = Signal()

    @Property(str, notify=shortcutsChanged)
    def shortcutSearch(self):
        return self.get_shortcut("search")

    @Property(str, notify=shortcutsChanged)
    def shortcutSelectAll(self):
        return self.get_shortcut("select_all")

    @Property(str, notify=shortcutsChanged)
    def shortcutClearSelection(self):
        return self.get_shortcut("clear_selection")

    @Property(str, notify=shortcutsChanged)
    def shortcutCopy(self):
        return self.get_shortcut("copy")

    @Property(str, notify=shortcutsChanged)
    def shortcutRefresh(self):
        return self.get_shortcut("refresh")

    @Property(str, notify=shortcutsChanged)
    def shortcutArchive(self):
        return self.get_shortcut("archive")

    @Property(str, notify=shortcutsChanged)
    def shortcutDelete(self):
        return self.get_shortcut("delete")

    @Property(str, notify=shortcutsChanged)
    def shortcutExpandAll(self):
        return self.get_shortcut("expand_all")

    @Property(str, notify=shortcutsChanged)
    def shortcutCollapseAll(self):
        return self.get_shortcut("collapse_all")

    @Property(str, notify=shortcutsChanged)
    def shortcutTopOfList(self):
        return self.get_shortcut("top_of_list")

    @Property(str, notify=shortcutsChanged)
    def shortcutQuickCopyView(self):
        return self.get_shortcut("quick_copy_view")

    @Property(str, notify=shortcutsChanged)
    def shortcutLibraryView(self):
        return self.get_shortcut("library_view")

    @Property(str, notify=shortcutsChanged)
    def shortcutUpdatesView(self):
        return self.get_shortcut("updates_view")

    @Property(str, notify=shortcutsChanged)
    def shortcutSettingsView(self):
        return self.get_shortcut("settings_view")

    @Property(str, notify=shortcutsChanged)
    def shortcutThemeToggle(self):
        return self.get_shortcut("theme_toggle")

    @Property(str, notify=shortcutsChanged)
    def shortcutSnap(self):
        return self.get_shortcut("snap")

    # --- Per-shortcut enabled state (read-only properties) ---

    @Property(bool, notify=shortcutsChanged)
    def shortcutSearchEnabled(self):
        return self.isShortcutEnabled("search")

    @Property(bool, notify=shortcutsChanged)
    def shortcutSelectAllEnabled(self):
        return self.isShortcutEnabled("select_all")

    @Property(bool, notify=shortcutsChanged)
    def shortcutClearSelectionEnabled(self):
        return self.isShortcutEnabled("clear_selection")

    @Property(bool, notify=shortcutsChanged)
    def shortcutCopyEnabled(self):
        return self.isShortcutEnabled("copy")

    @Property(bool, notify=shortcutsChanged)
    def shortcutRefreshEnabled(self):
        return self.isShortcutEnabled("refresh")

    @Property(bool, notify=shortcutsChanged)
    def shortcutArchiveEnabled(self):
        return self.isShortcutEnabled("archive")

    @Property(bool, notify=shortcutsChanged)
    def shortcutDeleteEnabled(self):
        return self.isShortcutEnabled("delete")

    @Property(bool, notify=shortcutsChanged)
    def shortcutExpandAllEnabled(self):
        return self.isShortcutEnabled("expand_all")

    @Property(bool, notify=shortcutsChanged)
    def shortcutCollapseAllEnabled(self):
        return self.isShortcutEnabled("collapse_all")

    @Property(bool, notify=shortcutsChanged)
    def shortcutTopOfListEnabled(self):
        return self.isShortcutEnabled("top_of_list")

    @Property(bool, notify=shortcutsChanged)
    def shortcutQuickCopyViewEnabled(self):
        return self.isShortcutEnabled("quick_copy_view")

    @Property(bool, notify=shortcutsChanged)
    def shortcutLibraryViewEnabled(self):
        return self.isShortcutEnabled("library_view")

    @Property(bool, notify=shortcutsChanged)
    def shortcutUpdatesViewEnabled(self):
        return self.isShortcutEnabled("updates_view")

    @Property(bool, notify=shortcutsChanged)
    def shortcutSettingsViewEnabled(self):
        return self.isShortcutEnabled("settings_view")

    @Property(bool, notify=shortcutsChanged)
    def shortcutThemeToggleEnabled(self):
        return self.isShortcutEnabled("theme_toggle")

    @Property(bool, notify=shortcutsChanged)
    def shortcutSnapEnabled(self):
        return self.isShortcutEnabled("snap")

    _is_recording_shortcut: bool = False

    @Property(bool, notify=isRecordingShortcutChanged)
    def isRecordingShortcut(self):  # type: ignore[reportRedeclaration]
        return getattr(self, "_is_recording_shortcut", False)

    @isRecordingShortcut.setter  # type: ignore[func-attr]
    def isRecordingShortcut(self, value):
        if getattr(self, "_is_recording_shortcut", False) != value:
            self._is_recording_shortcut = value
            if hasattr(self, "app") and self.app is not None:
                self.app._is_recording_shortcut = value
            self.isRecordingShortcutChanged.emit()

    def get_shortcut(self, key: str) -> str:
        """Gets a configured shortcut sequence."""
        return self.config.get("shortcuts", {}).get(key, "")

    @Slot(str, str)
    def setShortcut(self, action: str, sequence: str):
        """Sets a shortcut sequence for an action."""
        shortcuts = self.config.get("shortcuts", {})
        if action in shortcuts and shortcuts[action] != sequence:
            shortcuts[action] = sequence
            self.config.set("shortcuts", shortcuts)
            self.shortcutsChanged.emit()
            self.app._set_status(f"Shortcut for {action} set to: {sequence}")

    @Slot()
    def resetShortcuts(self):
        """Resets all shortcuts to defaults (enabled with default sequences)."""
        from skill_manager.core.config import DEFAULT_DISABLED_SHORTCUTS, DEFAULT_SHORTCUTS

        self.config.set("shortcuts", DEFAULT_SHORTCUTS.copy())
        self.config.set("disabled_shortcuts", DEFAULT_DISABLED_SHORTCUTS.copy())
        self.clearAllCollectionShortcuts()
        self.shortcutsChanged.emit()
        self.app._set_status("All shortcuts reset to defaults")

    @Slot(str, result=bool)
    def isShortcutEnabled(self, action: str) -> bool:
        """Returns True if the given shortcut action is enabled."""
        disabled: list[str] = self.config.get("disabled_shortcuts", [])
        return action not in disabled

    @Slot(str, bool)
    def setShortcutEnabled(self, action: str, enabled: bool) -> None:
        """Enable or disable a shortcut action. Emits shortcutsChanged."""
        disabled: list[str] = list(self.config.get("disabled_shortcuts", []))
        was_disabled = action in disabled
        if enabled and was_disabled:
            disabled.remove(action)
            self.config.set("disabled_shortcuts", disabled)
            self.shortcutsChanged.emit()
            self.app._set_status(f"Shortcut '{action}' enabled")
        elif not enabled and not was_disabled:
            disabled.append(action)
            self.config.set("disabled_shortcuts", disabled)
            self.shortcutsChanged.emit()
            self.app._set_status(f"Shortcut '{action}' disabled")

    @Slot(str)
    def setStatus(self, msg: str):
        """Sets the application status message from QML."""
        self.app._set_status(msg)
