## 2024-05-14 - Add Accessibility Labels to QML UI Components

**Learning:** QML components, such as `TextField`, `Button`, `Switch`, do not automatically have semantic accessibility attributes that screen readers use. They rely on the `Accessible` attached property.
**Action:** Will go through and add `Accessible.role`, `Accessible.name`, and `Accessible.description` (where appropriate) to key interactive UI elements like the search input, sidebar buttons, and glass toggle buttons.
