# Plan: Fix Screenshot Cancellation Ambiguous Shortcut

> Historical plan — preserved for traceability. See
> [`conductor/tracks.md`](tracks.md) for the active track record.

**Status:** Historical (completed) · **Date:** unknown

## Objective

Resolve the Qt ambiguous shortcut issue that causes the `Esc` key to be ignored when the screenshot overlay is active, ensuring the user can cancel the screenshot via keyboard.

## Scope

- **In:** `src/skill_manager/SkillManagerComponents/Main.qml`, `src/skill_manager/SkillManagerComponents/ScreenshotOverlay.qml`.
- **Out:** Other components.

## Action Items

1. **Resolve Ambiguity in `Main.qml`:**
   - Locate the `Shortcut` for `shortcutClearSelection` in `Main.qml`.
   - Update its `enabled` property to also depend on the visibility of the screenshot overlay:
     `enabled: !AppController.config_controller.isRecordingShortcut && !screenshotOverlay.visible`
   - Simplify its `onActivated` handler since it no longer needs to check for `screenshotOverlay.visible`:
     `onActivated: AppController.ui_controller.clearVisibleSelection()`

## Verification

- **Automated Tests:** `test_screenshot_feature.py` remains unaffected by UI shortcut routing but should still pass.
- **Manual Verification:**
  - Initiate a screenshot capture.
  - Press the `Esc` key.
  - Verify that the overlay closes and the main application window is restored, indicating the shortcut in `ScreenshotOverlay.qml` was successfully triggered without ambiguity.

## Cross-references

- Workflow: [`conductor/workflow.md`](workflow.md)
- Active tracks: [`conductor/tracks.md`](tracks.md)
- ADRs: [`../ADR_INDEX.md`](../ADR_INDEX.md)
