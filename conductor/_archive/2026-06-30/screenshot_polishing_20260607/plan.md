# Implementation Plan: Screenshot Feature Polishing

## Phase 1: Path and Emoji Fixes
- [x] Task 1.1: In `ScreenshotController.py`, use `_project_root_for_project` to ensure screenshots are saved in the project root's `.agents/screenshots` folder.
- [x] Task 1.2: Update `CATEGORY_EMOJI_MAP` in `src/skill_manager/core/categories.py` to use `🖼️` for `Screenshots`.
- [x] Task 1.3: Update `format_project_skill_reference` in `quick_copy.py` to handle screenshots without appending `/SKILL.md`.

## Phase 2: Inspector UI Improvements
- [x] Task 2.1: Update `SkillInspector.qml` to hide metadata rectangle when `skill.is_screenshot` is true.
- [x] Task 2.2: Update `SkillInspector.qml` to hide "Implementation Details" section when `skill.is_screenshot` is true.
- [x] Task 2.3: Ensure `screenshotPreview` image source uses the correct path format (normalized `file:///` path).

## Phase 3: Validation
- [x] Task 3.1: Update `tests/test_screenshot_feature.py` to verify root path resolution.
- [x] Task 3.2: Verify clipboard reference formatting for Gemini CLI.
- [x] Task 3.3: Run all tests.
