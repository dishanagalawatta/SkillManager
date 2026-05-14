## 2025-05-14 - Add tooltips to collapsed sidebar icons
**Learning:** Icon-only navigation can be ambiguous, particularly when sidebars collapse to save space. Providing tooltips that surface the original text label restores the missing context for screen readers and sighted users exploring the UI.
**Action:** Always verify that collapsing/responsive behaviors that hide labels in favor of icons include `ToolTip` or `aria-label` equivalents.
