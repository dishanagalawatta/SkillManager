# Plan: Configurable Screenshot Cancel Shortcut

> Historical plan — preserved for traceability. See
> [`conductor/tracks.md`](tracks.md) for the active track record.

**Status:** Historical (completed) · **Date:** unknown

## Objective

Replace the hardcoded ESC shortcut in ScreenshotOverlay with a user-configurable keybinding, integrated into the existing Settings > Shortcuts system.

## Scope

- **In:**
  - Add `screenshot_cancel` to config defaults and controller.
  - Replace hardcoded ESC in ScreenshotOverlay with config binding.
  - Add "Cancel Screenshot" row to ShortcutsSettings UI.
  - Unit test for new config key.
- **Out:**
  - No behavior change (ESC remains default).
  - No changes to screenshot capture/redaction logic.
  - No changes to other shortcuts.

## Action Items

- [ ] Add `screenshot_cancel: "Esc"` to `DEFAULT_SHORTCUTS` in `src/skill_manager/core/config.py`
- [ ] Add `shortcutScreenshotCancel` property and getter to `ConfigController` in `src/skill_manager/controllers/config_controller.py`
- [ ] Replace hardcoded `"Escape"` sequence with `AppController.config_controller.shortcutScreenshotCancel` in `src/skill_manager/SkillManagerComponents/ScreenshotOverlay.qml`
- [ ] Add "Cancel Screenshot" `KeySequenceCapture` row to `src/skill_manager/SkillManagerComponents/views/ShortcutsSettings.qml`
- [ ] Add unit test for `screenshot_cancel` config key in `tests/test_screenshot_feature.py`
- [ ] Run lint: `uv run ruff check src/skill_manager/core/config.py src/skill_manager/controllers/config_controller.py`
- [ ] Run format: `uv run ruff format src/skill_manager/core/config.py src/skill_manager/controllers/config_controller.py`
- [ ] Run tests: `uv run pytest tests/test_screenshot_feature.py`

## Verification

- Run `python run_tests.py` to confirm 0 failures and lint clean.

## Cross-references

- Workflow: [`conductor/workflow.md`](workflow.md)
- Active tracks: [`conductor/tracks.md`](tracks.md)
- ADRs: [`../ADR_INDEX.md`](../ADR_INDEX.md)
