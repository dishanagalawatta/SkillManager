# Plan: Fix Screenshot Cancellation Shortcut Registration and Event Flow

> Historical plan — preserved for traceability. See
> [`conductor/tracks.md`](tracks.md) for the active track record.

**Status:** Historical (completed) · **Date:** unknown

## Objective

Ensure the screenshot process can be reliably canceled using `Esc` when auto-minimize is enabled. The previous fix failed because setting `overlay.visible = false` before `overlay.close()` prevents the `closing` event (and thus `onClosing`) from being emitted in Qt QML Windows.

## Scope

- **In:** `src/skill_manager/SkillManagerComponents/ScreenshotOverlay.qml`.
- **Out:** Other components.

## Action Items

1. **Fix `ScreenshotOverlay.qml` Shortcut Logic:**
   - Remove `overlay.visible = false` from the `Shortcut`'s `onActivated` handler.
   - Simply call `AppController.screenshot_controller.cancelCapture()` explicitly, followed by `overlay.close()`. Or simply call `overlay.close()` without hiding it first.
   - Also, update the "Cancel" `ActionButton` in `ScreenshotOverlay.qml` which currently does:
     ```qml
     onClicked: {
         overlay.visible = false
         overlay.close()
     }
     ```
     This has the exact same bug! It should just be `overlay.close()`.

2. **Add Global Shortcut for the Delay Phase (Optional but good):**
   - If the user presses `Esc` during the 300ms minimize delay, they might want to cancel. But since the main window is minimized, `Esc` is swallowed by the OS. It's an edge case, but the main issue is that even when the overlay opens, `Esc` and the "Cancel" button don't work due to `visible = false` blocking `onClosing`.

## Verification

- **Automated Tests:** `test_screenshot_feature.py` should remain unaffected.
- **Manual Verification:**
  - Verify the Cancel button in the overlay toolbox properly cancels and restores the app.
  - Verify the `Esc` key properly cancels and restores the app.

## Cross-references

- Workflow: [`conductor/workflow.md`](workflow.md)
- Active tracks: [`conductor/tracks.md`](tracks.md)
- ADRs: [`../ADR_INDEX.md`](../ADR_INDEX.md)
