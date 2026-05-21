## 2024-05-18 - Missing Accessible.name and Accessible.role in TextField and TextArea
**Learning:** QML `TextField` and `TextArea` elements in this app's dialogs and views frequently lack `Accessible.name` and `Accessible.role` properties, making them inaccessible to screen readers. QML doesn't automatically infer these from placeholders or labels.
**Action:** Always add `Accessible.role: Accessible.EditableText` and a descriptive `Accessible.name` to all `TextField` and `TextArea` components to ensure screen reader support.
