# Plan

Create a reusable QML component that wraps Qt's native WheelHandler to apply a configurable scroll speed multiplier to ListViews and ScrollViews, and expose a setting in the Settings tab to control this value.

## Scope

- In: Adding a global scroll speed configuration to Python backend (AppConfig), exposing it to QML via ConfigController, and creating `SmoothListView.qml` & `SmoothScrollView.qml` to replace existing native views. Adding UI in SettingsView.
- Out: Custom kinetic physics, third-party libraries (unnecessary in PySide6).

## Action Items

- [x] Task 1.1: Add `scroll_speed_multiplier` (default 1.0) to `AppConfig` in `src/skill_manager/core/schemas.py`.
- [x] Task 1.2: Add `@Property` for `scrollSpeedMultiplier` to `ConfigController` in `src/skill_manager/controllers/config_controller.py`, with a setter that saves to config.
- [x] Task 2.1: Create `src/skill_manager/SkillManagerComponents/SmoothListView.qml` combining `ListView` with a `WheelHandler` bound to `configController.scrollSpeedMultiplier`.
- [x] Task 2.2: Create `src/skill_manager/SkillManagerComponents/SmoothScrollView.qml` combining `ScrollView` with a `WheelHandler` bound to `configController.scrollSpeedMultiplier`.
- [x] Task 3.1: Replace usages of `ListView` with `SmoothListView` in `LibraryView.qml`, `QuickCopyView.qml`, `UpdatesView.qml`, etc.
- [x] Task 3.2: Replace usages of `ScrollView` with `SmoothScrollView` in `SkillInspector.qml`, `SettingsView.qml`, `PackageEditDialog.qml`, etc.
- [x] Task 4.1: Add a slider in `SettingsView.qml` (under General tab) to let the user adjust `configController.scrollSpeedMultiplier` between 0.5 and 5.0.
- [x] Task 5.1: Test UI scrolling across all views to ensure the multiplier works and scrollbars update correctly.

## Open Questions

- None.
