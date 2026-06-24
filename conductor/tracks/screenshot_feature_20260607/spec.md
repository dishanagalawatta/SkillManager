# Screenshot and Redaction Feature

## 1. Overview
A new screenshot utility integrated directly into SkillManager. It allows users to quickly grab a selectable portion of their screen, dynamically draw black redaction boxes over sensitive information, save the result directly into the active project's `.agents/screenshots/` directory, copy it to the clipboard, and display it in the QuickCopy view under a "Screenshot" category.

## 2. Understanding Summary
- **What:** Screenshot tool with redaction capabilities.
- **Why:** To quickly capture, redact sensitive info, and save snippets/images into the active project for easy copying/reference.
- **Who:** Developers/users using SkillManager.
- **Storage:** Saved natively as images in `.agents/screenshots/`.
- **Workflow:** Freeze screen -> Select area -> Toolbox appears -> Draw redactions (black boxes) -> Press Enter to capture.
- **Tech:** Native PySide6 (QScreen & Frameless Window).
- **Non-goals:** Not a full image editor, just simple redaction (no text, arrows, blur, etc.).

## 3. Assumptions
- **Discovery:** `quick_copy.py` will be updated to scan `.agents/screenshots/` and map images to a virtual "Screenshot" category.
- **Naming:** Auto-generated names (e.g., `Screenshot_YYYYMMDD_HHMMSS.png`).
- **Preview:** `SkillInspector.qml` will be updated to display a raw image if the "skill" is an image rather than a `.md` file.

## 4. Decision Log
- **Technology Approach:** Decided to use pure PySide6/QML for the overlay instead of external libraries like `mss`. This keeps the app self-contained and allows for a smooth, native-feeling QML UI for drawing redactions.
- **Workflow:** Decided on a "Select Area Then Redact" workflow. The screen freezes, the user selects the primary crop area, and then they can draw redactions *inside* that area before finalizing.
- **Data Handoff:** QML handles the visual drawing and passes coordinates (crop box + redaction boxes) back to Python. Python performs the actual `QPainter` image manipulation, saving, and clipboard operations.

## 5. Design Details

### 5.1 Backend Capture (Python)
- A new controller method `take_screenshot()` captures the screen via `QGuiApplication.primaryScreen().grabWindow(0)`.
- The captured `QPixmap` is exposed to QML via a custom `QQuickImageProvider`.
- Python triggers the opening of `ScreenshotOverlay.qml`.

### 5.2 Frontend Overlay (QML)
- `ScreenshotOverlay.qml`: A frameless, full-screen transparent window.
- **Selecting State**: Displays the frozen screen. A `MouseArea` tracks dragging to define a `cropRect`. Unselected areas are dimmed.
- **Redacting State**: Inside the `cropRect`, dragging creates black `Rectangle` elements.
- A floating toolbox provides "Cancel" (Esc) and "Save" (Enter) buttons.
- On Save, it passes `cropRect` and `redaction_rects` to Python.

### 5.3 Backend Processing & Storage (Python)
- Python receives the coordinates, crops the original `QPixmap`, and paints solid black boxes over the redaction areas.
- Saves the file to `[Active Project]/.agents/screenshots/Screenshot_YYYYMMDD_HHMMSS.png`.
- Copies the image to the clipboard.

### 5.4 Discovery & QuickCopy Integration
- Update `discover_single_project` in `src/skill_manager/core/quick_copy.py` to also look for images in `.agents/screenshots/`.
- These images are mapped to dictionaries where `main_category` is "Screenshot" and `skill_md_path` is the image path.
- Update `SkillInspector.qml` to render an `<Image>` if the file extension is `.png`, `.jpg`, etc., instead of parsing it as Markdown.