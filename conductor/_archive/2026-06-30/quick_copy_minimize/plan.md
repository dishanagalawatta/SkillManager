# Plan

Implement "Auto-minimize on Quick Copy" feature.

## Scope

- In: Adding configuration, UI toggle, and logic to minimize the window when copying from the QuickCopy view.
- Out: Minimizing from other views (e.g., Library).

## Action Items

### Phase 1: Configuration

- [x] Task 1.1: Update `AppConfig` in `src/skill_manager/core/schemas.py` to include `auto_minimize_on_quick_copy: bool = False`.
- [x] Task 1.2: Add `autoMinimizeOnQuickCopy` property and `autoMinimizeOnQuickCopyChanged` signal to `ConfigController` in `src/skill_manager/controllers/config_controller.py`.

### Phase 2: Logic and UI

- [x] Task 2.1: In `src/skill_manager/controllers/ops_controller.py`, add `minimizeAppRequested` signal. Update copy methods (`copySkillToClipboard`, `copySelectedSkillsToClipboard`, `copySkillReference`) to emit this signal if `autoMinimizeOnQuickCopy` is true and `app.ui_controller.currentView` is "QuickCopy".
- [x] Task 2.2: In `src/skill_manager/SkillManagerComponents/Main.qml`, add a `Connections` block targeting `AppController.ops_controller` to call `window.showMinimized()` on `minimizeAppRequested`.
- [x] Task 2.3: In `src/skill_manager/SkillManagerComponents/views/SettingsView.qml`, add a toggle switch for "Auto-minimize on Quick Copy" bound to `AppController.config_controller.autoMinimizeOnQuickCopy`.

### Phase 3: Validation

- [x] Task 3.1: Update `tests/test_config_controller.py` to verify the new configuration property.
- [x] Task 3.2: Update `tests/test_ops_controller.py` to verify the `minimizeAppRequested` signal is emitted correctly based on view and config.
