# Implementation Plan: Screenshot Feature Fixes

## Phase 1: QML UI Fixes
- [x] Task 1.1: Update `ScreenshotOverlay.qml` to set `visibility: Window.Hidden` by default.
- [x] Task 1.2: Add `z: 1000` to the toolbox in `ScreenshotOverlay.qml`.
- [x] Task 1.3: Add `context: Qt.ApplicationShortcut` to the `Shortcut` components in `ScreenshotOverlay.qml` so Escape works globally.

## Phase 2: Python Backend Fixes
- [x] Task 2.1: In `ScreenshotController.py`, update project resolution logic to use `project_label` matching to find the correct absolute path instead of blindly using the filter string.
- [x] Task 2.2: In `ScreenshotController.py`, update clipboard logic to check `self.app.clientFormat`. If `"Gemini CLI"`, copy `@.agents/screenshots/{filename}` instead of the image.
- [x] Task 2.3: In `quick_copy.py`, change the synthesized skill's `main_category` from `"Screenshot"` to `"Screenshots"`.

## Phase 3: Validation
- [x] Task 3.1: Update `tests/test_screenshot_feature.py` to test the new save path logic and the clipboard behavior for Gemini CLI.
- [x] Task 3.2: Run `uv run pytest tests/test_screenshot_feature.py` to verify the fixes.
- [x] Task 3.3: Run full `uv run pytest` to ensure no regressions.