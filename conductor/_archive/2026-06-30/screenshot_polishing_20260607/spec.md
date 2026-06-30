# Screenshot Feature Polishing

## 1. Overview
Address path resolution issues, categorization emojis, and inspector redundant data for the screenshot feature.

## 2. Understanding Summary
- **Wrong Path:** Screenshots are saved in a nested `.agents/skills/.agents/screenshots` folder because the project path is resolved to the skills directory instead of the project root.
- **Category Emoji:** Change "Screenshots" emoji from 📸 to 🖼️.
- **Inspector Data:** Hide metadata (Risk, Source, Date) and "Implementation Details" for screenshots. Ensure image preview works correctly.
- **Redundant Grouping:** Clean up the "two time showing screenshots" issue (likely the Special -> Screenshots nesting) and fix path references in clipboard.

## 3. Assumptions
- `_project_root_for_project` in `quick_copy.py` correctly extracts the project root from a path containing `.agents/skills`.
- Virtual skills for screenshots should use a different path reference logic than standard skills (no `/SKILL.md` suffix).

## 4. Design Details
- **Path Resolution:** In `ScreenshotController`, wrap `project_path` with `_project_root_for_project`.
- **Emoji Update:** Modify `CATEGORY_EMOJI_MAP`.
- **Inspector Tweak:** Update `SkillInspector.qml` to conditionalize metadata and implementation sections.
- **Path Reference:** Fix `format_project_skill_reference` in `quick_copy.py` to handle images properly.
- **QuickCopy Categorization:** Ensure Screenshots sub-category is enough, or maybe rename the virtual skill's category. Currently it's "Capture". We'll keep it under "Screenshots" subcategory.
