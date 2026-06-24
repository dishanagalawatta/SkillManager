# Implementation Plan: Screenshot Feature

## Phase 1: Backend Capture Setup
- [x] Task 1.1: Create `ImageProvider` class in Python (inheriting from `QQuickImageProvider`) to hold the captured `QPixmap`.
- [x] Task 1.2: Add `take_screenshot()` method in `AppController` (or a dedicated controller) that captures the primary screen.
- [x] Task 1.3: Expose the `ImageProvider` to the QML engine during app initialization.

## Phase 2: QML Overlay Interface
- [x] Task 2.1: Create `ScreenshotOverlay.qml` as a frameless, transparent, fullscreen `Window`.
- [x] Task 2.2: Add logic to display the image from the `ImageProvider` as the background.
- [x] Task 2.3: Implement the "Selecting" state: `MouseArea` to draw the initial crop boundary and dim the unselected regions.
- [x] Task 2.4: Implement the "Redacting" state: dynamic creation of black `Rectangle` components inside the crop area.
- [x] Task 2.5: Add a floating toolbox with "Cancel" and "Save" buttons.
- [x] Task 2.6: Connect "Save" to pass `cropRect` and `redactionRects` back to Python.

## Phase 3: Image Processing & Saving
- [x] Task 3.1: Add `save_screenshot(crop_rect, redactions)` slot in Python.
- [x] Task 3.2: Use `QPainter` to crop the original `QPixmap` and draw solid black rectangles over the specified redaction coordinates.
- [x] Task 3.3: Save the final `QPixmap` to the active project folder at `.agents/screenshots/Screenshot_YYYYMMDD_HHMMSS.png`.
- [x] Task 3.4: Copy the final image to the system clipboard using `QGuiApplication.clipboard()`.

## Phase 4: QuickCopy Integration
- [x] Task 4.1: Update `discover_single_project` in `src/skill_manager/core/quick_copy.py` to scan `.agents/screenshots/` and synthesize Skill dictionaries for images.
- [x] Task 4.2: Update `SkillInspector.qml` to detect image extensions and render an `<Image>` element instead of Markdown text.
- [x] Task 4.3: Add a global shortcut or a UI button to trigger the screenshot feature.

## Phase 5: Verification
- [x] Task 5.1: Test full screen capture on different monitor scales (DPI handling).
- [x] Task 5.2: Test redaction coordinates alignment (ensure black boxes map perfectly from QML to the saved image).
- [x] Task 5.3: Verify clipboard functionality and image display in QuickCopy.