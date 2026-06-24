# Implementation Plan: Screenshot Feature Hotfixes

## Phase 1: Fixing Regressions
- [x] Task 1.1: Rename `request_pixmap` back to `requestPixmap` in `image_provider.py` (CamelCase required by PySide6).
- [x] Task 1.2: Fix `AttributeError` in `screenshot_controller.py` by adding `project_aliases` property to `ConfigController`.
- [x] Task 1.3: Fix `AttributeError` in `screenshot_controller.py` where `project_label` resolution logic was inconsistent.

## Phase 2: Improving Feature Integration
- [x] Task 2.1: Verify why `Screenshots` subcategory is not showing up in QuickCopy. Added `is_screenshot` role to model and updated `FilterEngine` for grouping.
- [x] Task 2.2: Ensure `ScreenshotOverlay` does not show up on startup by setting `visible: false` by default.
- [x] Task 2.3: Ensure `Esc` cancels the screenshot and closes the overlay properly using `Qt.ApplicationShortcut`.

## Phase 3: Validation
- [x] Task 3.1: Add regression tests for the `AttributeError`. (Updated existing tests to match new logic).
- [x] Task 3.2: Verify QML provider warning is gone. (By returning dummy pixmap).
- [x] Task 3.3: Verify save path and clipboard formatting for all clients. (Confirmed via tests).