## 2026-05-18 - Custom Button Focus States
**Learning:** Custom QML controls lack built-in keyboard focus styling, which is a major accessibility issue for keyboard users who rely on the 'Tab' key to navigate.
**Action:** Always include `control.visualFocus` in the `border.color` and `border.width` properties of custom buttons to provide clear visual feedback during keyboard navigation.
