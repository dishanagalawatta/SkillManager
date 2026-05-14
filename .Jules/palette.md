## 2025-05-14 - Add tooltips to collapsed sidebar icons
**Learning:** Icon-only navigation can be ambiguous, particularly when sidebars collapse to save space. Providing tooltips that surface the original text label restores the missing context for screen readers and sighted users exploring the UI.
**Action:** Always verify that collapsing/responsive behaviors that hide labels in favor of icons include `ToolTip` or `aria-label` equivalents.
## 2024-05-14 - Add Accessibility Labels to QML UI Components

**Learning:** QML components, such as `TextField`, `Button`, `Switch`, do not automatically have semantic accessibility attributes that screen readers use. They rely on the `Accessible` attached property.
**Action:** Will go through and add `Accessible.role`, `Accessible.name`, and `Accessible.description` (where appropriate) to key interactive UI elements like the search input, sidebar buttons, and glass toggle buttons.
