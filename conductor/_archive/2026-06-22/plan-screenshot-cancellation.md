# Plan: Fix Screenshot Cancellation with Auto-Minimize

> Historical plan — preserved for traceability. See
> [`conductor/tracks.md`](tracks.md) for the active track record.

**Status:** Historical (completed) · **Date:** unknown

## Objective

Ensure the screenshot process can be reliably canceled using the designated shortcut (default: `Esc`), especially when the "auto-minimize on screenshot" feature is enabled.

## Scope

- **In:** `src/skill_manager/SkillManagerComponents/ScreenshotOverlay.qml`, `src/skill_manager/SkillManagerComponents/Main.qml`.
- **Out:** Other components.

## Action Items

1. **Add Shortcut to `ScreenshotOverlay.qml`:**
   - Define a new `Shortcut` element within the `ScreenshotOverlay` component.
   - Bind its `sequence` to `AppController.config_controller.shortcutClearSelection`.
   - Set its `context` to `Qt.WindowShortcut` so it activates when the overlay window has focus.
   - In its `onActivated` handler, set `overlay.visible = false` and call `overlay.close()`. This will trigger the existing `onClosing` signal handler, which in turn calls `AppController.screenshot_controller.cancelCapture()` and restores the main window.

## Verification

- **Manual Verification:**
  - Enable "Auto-minimize on screenshot" in settings.
  - Initiate a screenshot capture. The app should minimize and the overlay should appear.
  - Press the `Esc` key.
  - Verify that the overlay closes and the main application window is restored.
  - Verify cancellation still works when auto-minimize is disabled.
- **Automated Tests:**
  - The existing `test_screenshot_feature.py` should continue to pass, as the core signal logic (`cancelCapture()`) remains intact.

## Cross-references

- Workflow: [`conductor/workflow.md`](workflow.md)
- Active tracks: [`conductor/tracks.md`](tracks.md)
- ADRs: [`../ADR_INDEX.md`](../ADR_INDEX.md)
