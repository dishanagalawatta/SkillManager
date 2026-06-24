# Screenshot Feature Hotfixes

## 1. Overview
This track addresses regressions and bugs found after the initial implementation of the screenshot feature.

## 2. Understanding Summary
- **AttributeError:** `ConfigController` missing `project_aliases`.
- **QML Warning:** `requestPixmap` was renamed to `request_pixmap`, breaking the hook from QML.
- **Startup Trigger:** The screenshot overlay is appearing prematurely.
- **Escape Key:** Shortcut is not working as expected.
- **QuickCopy Integration:** Screenshots are not listed.

## 3. Assumptions
- PySide6 requires the exact CamelCase `requestPixmap` for overrides.
- `project_aliases` should be accessed via a property or directly from `self.app._project_aliases`.

## 4. Design Details
- Revert method name in `image_provider.py`.
- Add `project_aliases` property to `ConfigController`.
- Correct the logic in `screenshot_controller.py`.
- Ensure `ScreenshotOverlay.qml` handles its lifecycle correctly.