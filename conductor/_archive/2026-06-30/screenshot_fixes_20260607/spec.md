# Screenshot Feature Fixes

## 1. Overview
This track addresses several user-reported issues with the newly implemented screenshot feature, including startup visibility, shortcut cancellation, save location, clipboard formatting, toolbox visibility, and categorization in QuickCopy.

## 2. Understanding Summary
- **What:** Fix 6 specific bugs in the screenshot feature.
- **Why:** The feature behaves incorrectly on startup, save paths are broken if active project isn't resolved properly, clipboard formatting needs to be client-specific, and the UI has layering issues (toolbox not visible, esc not working). Also, the category is not showing up properly.
- **Who:** Developers contributing to SkillManager.
- **Constraints:** Must follow the existing TDD and UI design patterns.

## 3. Assumptions
- The "app opens with screenshot button triggered" issue is due to `ScreenshotOverlay.qml` defaulting to `visible: true` (or `visibility: Window.FullScreen`) upon startup instead of waiting for the signal.
- The escape key issue is because the `Shortcut` in QML needs `context: Qt.ApplicationShortcut` to catch key presses even when focus is lost, and the overlay must hide itself properly.
- The save path issue occurs because `self.app.quickCopyModel.projectFilter` holds the project *name* (label) or is empty, so we must resolve it to the absolute path of the project.
- The clipboard issue requires checking `self.app.clientFormat`. If it's "Gemini CLI", it should copy the text `@.agents/screenshots/{filename}`. Otherwise, it copies the image.
- The toolbox visibility issue is a Z-index problem (`z: 1000` is needed).
- The QuickCopy category issue is because QuickCopy only parses "Screenshot" but we need to ensure the emoji map and categories align, and maybe `is_screenshot` skills need to be correctly categorized under "Screenshots".

## 4. Decision Log
- **Save Path:** We will resolve the active project path by matching `self.app.quickCopyModel.projectFilter` against loaded projects using `project_label()`.
- **Clipboard:** We will add a condition for `Gemini CLI` to copy the requested formatted string.
- **UI Tweaks:** We will set `visibility: Window.Hidden` by default in QML, add `z: 1000` to the toolbox, and ensure `Qt.ApplicationShortcut` is used for the Esc key.
- **Category:** We will change `main_category` to `"Screenshots"` in `quick_copy.py` to match the expected category group.

## 5. Design Details
### Phase 1: QML UI Fixes
- `ScreenshotOverlay.qml`:
  - Set `visibility: Window.Hidden` (or `visible: false`).
  - Set `z: 1000` on the toolbox Rectangle.
  - Add `context: Qt.ApplicationShortcut` to the `Shortcut` elements.
  - In `onShowOverlay`, call `overlay.showFullScreen()` or `overlay.visible = true`.

### Phase 2: Python Backend Fixes
- `ScreenshotController.py`:
  - Update `saveScreenshot` to resolve the actual project path using `project_label`.
  - Update clipboard logic to check `self.app.clientFormat == "Gemini CLI"` and copy `@.agents/screenshots/Screenshot_XXX.png`.
- `quick_copy.py`:
  - Change `"main_category": "Screenshot"` to `"main_category": "Screenshots"`.
  - Ensure the fallback folder is correct.

### Phase 3: Validation
- Update tests to cover the new save path resolution and clipboard logic.