"""Per-collection keyboard shortcuts with auto-claim semantics for the ConfigController facade."""

from PySide6.QtCore import Slot


class CollectionShortcutsMixin:
    """Per-collection shortcut binding, enable/disable, and clearing.

    Emits the facade-level ``shortcutsChanged``/``customCollectionsChanged``
    signals, which are re-declared as canonical class attributes on the
    facade class.
    """

    def _claim_sequence(self, seq: str, owner_name: str) -> list[str]:
        """Forcibly clears `seq` from any built-in action and any other collection.

        Returns a human-readable list of entities that were freed so the
        caller can include them in a status message.
        """
        if not seq:
            return []

        freed: list[str] = []

        # 1. Free from built-in shortcuts
        shortcuts = self.config.get("shortcuts", {})
        for action, bound_seq in list(shortcuts.items()):
            if bound_seq == seq:
                shortcuts[action] = ""
                freed.append(action)

        if freed:
            self.config.set("shortcuts", shortcuts)

        # 2. Free from other collections
        for name, entry in self.app._custom_collections.items():
            if name == owner_name:
                continue
            if isinstance(entry, dict) and entry.get("shortcut") == seq:
                entry["shortcut"] = ""
                freed.append(name)

        if freed:
            self.config.set("custom_collections", self.app._custom_collections)
            self.shortcutsChanged.emit()
            self.customCollectionsChanged.emit()

        return freed

    @Slot(str, str)
    def setCollectionShortcut(self, name: str, seq: str):
        """Sets a shortcut sequence for a collection with auto-claim semantics."""
        entry = self.app._custom_collections.get(name)
        if entry is None:
            return
        if not isinstance(entry, dict):
            return
        old = entry.get("shortcut", "")
        if old == seq:
            return

        freed = self._claim_sequence(seq, name)

        entry["shortcut"] = seq
        self.config.set("custom_collections", self.app._custom_collections)
        self.shortcutsChanged.emit()
        self.customCollectionsChanged.emit()

        msg = (
            f"Collection '{name}' bound to {seq}"
            if seq
            else f"Collection '{name}' shortcut cleared"
        )
        if freed:
            msg += f" (reassigned from: {', '.join(freed)})"
        self.app._set_status(msg)

    @Slot(str, bool)
    def setCollectionShortcutEnabled(self, name: str, enabled: bool):
        """Enable or disable the shortcut for a collection without losing the sequence."""
        entry = self.app._custom_collections.get(name)
        if entry is None or not isinstance(entry, dict):
            return
        old = entry.get("shortcut_enabled", True)
        if old == enabled:
            return
        entry["shortcut_enabled"] = enabled
        self.config.set("custom_collections", self.app._custom_collections)
        self.customCollectionsChanged.emit()

    @Slot(str, result=str)
    def getCollectionShortcut(self, name: str) -> str:
        """Returns the shortcut sequence for a named collection."""
        entry = self.app._custom_collections.get(name, {})
        if isinstance(entry, dict):
            return entry.get("shortcut", "")
        return ""

    @Slot(str, result=bool)
    def getCollectionShortcutEnabled(self, name: str) -> bool:
        """Returns whether the shortcut is enabled for a named collection."""
        entry = self.app._custom_collections.get(name, {})
        if isinstance(entry, dict):
            return entry.get("shortcut_enabled", True)
        return True

    def clearAllCollectionShortcuts(self):
        """Clears all collection shortcuts. Called by resetShortcuts."""
        changed = False
        for _name, entry in self.app._custom_collections.items():
            if isinstance(entry, dict) and (
                entry.get("shortcut") or not entry.get("shortcut_enabled", True)
            ):
                entry["shortcut"] = ""
                entry["shortcut_enabled"] = True
                changed = True
        if changed:
            self.config.set("custom_collections", self.app._custom_collections)
            self.customCollectionsChanged.emit()
