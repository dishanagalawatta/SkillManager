# Plan

> Historical plan — preserved for traceability. See
> [`conductor/tracks.md`](tracks.md) for the active track record.

**Status:** Historical (completed) · **Date:** unknown

## Objective

Implement "Auto-minimize on Quick Copy" feature.

## Scope

- **In:** Adding configuration, UI toggle, and logic to minimize the window when copying from the QuickCopy view.
- **Out:** Minimizing from other views (e.g., Library).

## Action Items

### Phase 1: Configuration

- [ ] Task 1.1: Update `AppConfig` in `src/skill_manager/core/schemas.py` to include `auto_minimize_on_quick_copy: bool = False`.
- [ ] Task 1.2: Add `autoMinimizeOnQuickCopy` property and `autoMinimizeOnQuickCopyChanged` signal to `ConfigController` in `src/skill_manager/controllers/config_controller.py`.

### Phase 2: Logic and UI

- [ ] Task 2.1: In `src/skill_manager/controllers/ops_controller.py`, add `minimizeAppRequested` signal. Update copy methods (`copySkillToClipboard`, `copySelectedSkillsToClipboard`, `copySkillReference`) to emit this signal if `autoMinimizeOnQuickCopy` is true and `app.ui_controller.currentView` is "QuickCopy".
- [ ] Task 2.2: In `src/skill_manager/SkillManagerComponents/Main.qml`, add a `Connections` block targeting `AppController.ops_controller` to call `window.showMinimized()` on `minimizeAppRequested`.
- [ ] Task 2.3: In `src/skill_manager/SkillManagerComponents/views/SettingsView.qml`, add a toggle switch for "Auto-minimize on Quick Copy" bound to `AppController.config_controller.autoMinimizeOnQuickCopy`.

### Phase 3: Validation

- [ ] Task 3.1: Update `tests/test_config_controller.py` to verify the new configuration property.
- [ ] Task 3.2: Update `tests/test_ops_controller.py` to verify the `minimizeAppRequested` signal is emitted correctly based on view and config.

## Verification

- Run `python run_tests.py` to confirm 0 failures and lint clean.

## Cross-references

- Workflow: [`conductor/workflow.md`](workflow.md)
- Active tracks: [`conductor/tracks.md`](tracks.md)
- ADRs: [`../ADR_INDEX.md`](../ADR_INDEX.md)
