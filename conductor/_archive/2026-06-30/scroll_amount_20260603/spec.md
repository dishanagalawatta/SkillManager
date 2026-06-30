# Scroll Amount Adjustment Spec

## Overview
Users require a way to adjust the mouse wheel scroll speed in the application, as default QML scrolling can be too slow or fast depending on the system configuration.

## Requirements
- Add a new AppConfig setting `scroll_speed_multiplier` (float).
- Expose this setting to QML via `ConfigController`.
- Provide a slider in `SettingsView.qml` to adjust the speed between 0.5x and 5.0x.
- Create reusable `SmoothListView` and `SmoothScrollView` components in QML using `WheelHandler` to intercept scroll events and multiply the scroll step by the config value.
- Update existing lists and scroll areas to use the new smooth components.

## Technical Strategy
We will not use third-party libraries. In Qt6/PySide6, `WheelHandler` provides a clean, native way to intercept scroll events without affecting kinetic scrolling or scrollbars.
