# Plan

Add per-shortcut on/off toggle with sequence memory. Each of the 16 actions gets a `GlassSwitch` in `ShortcutsSettings.qml`. Disabling clears the sequence; re-enabling restores it. `Reset to Defaults` re-enables all + restores defaults.

## Scope

- In: `core/config.py`, `controllers/config_controller.py`, `app.py`, `Main.qml`, `ScreenshotOverlay.qml`, `views/ShortcutsSettings.qml`, tests
- Out: No changes to `core/schemas.py`, `core/global_hotkey.py` (no new methods), `SkillInspector.qml`

## Action Items

### Phase 1: Core (config + controller)

- [ ] Task 1.1: Add `DEFAULT_DISABLED_SHORTCUTS = []` to `core/config.py` and ensure `disabled_shortcuts` is persisted on first load (migration)
- [ ] Task 1.2: Add `get_disabled_shortcuts()`, `set_disabled_shortcuts()`, `isShortcutEnabled(action)`, `setShortcutEnabled(action, bool)` to `ConfigController`
- [ ] Task 1.3: Update `resetShortcuts()` to also clear `disabled_shortcuts`

### Phase 2: Integration (app.py + QML)

- [ ] Task 2.1: Add `shortcutEnabled` properties per action to `AppController` (`app.py`), wired to `shortcutsChanged`
- [ ] Task 2.2: Update `enabled:` bindings in `Main.qml` to include `&& AppController.config_controller.isShortcutEnabled("action")`
- [ ] Task 2.3: Update `enabled:` bindings in `ScreenshotOverlay.qml` for `clear_selection` and `screenshot`
- [ ] Task 2.4: Update `_on_shortcuts_changed` in `app.py` to unregister pynput when `screenshot` is disabled
- [ ] Task 2.5: Add 3-column layout to `ShortcutsSettings.qml` (label / sequence / `GlassSwitch`)

### Phase 3: Tests + Lint

- [ ] Task 3.1: Write unit tests for `setShortcutEnabled`, `isShortcutEnabled`, and `resetShortcuts` in `tests/test_config_controller.py`
- [ ] Task 3.2: Run `python run_tests.py` — confirm 0 failures, lint clean

## Open Questions

- None remaining
