# Auto-minimize on Quick Copy

## Objective
Implement an optional feature that automatically minimizes the SkillManager application window when a user copies an item from the "Quick Copy" view.

## Requirements
- A new configuration setting `auto_minimize_on_quick_copy` must be added and saved persistently.
- The Settings UI must include a toggle to enable/disable this feature.
- When enabled, copying a skill or reference from the Quick Copy view (via button or shortcut) must minimize the application window.
- The feature should *only* trigger from the Quick Copy view, not from the Library or Updates view.

## Out of Scope
- Modifying how screenshots trigger minimization (this is already handled separately).
- Changes to the system tray behavior.