# Refactoring Plan: ScreenshotController and Image Processing (SDET)

> Historical refactor plan — preserved for traceability. See
> [`conductor/tracks.md`](tracks.md) for the active track record.

**Status:** Historical (completed) · **Date:** unknown

## Background & Motivation

The `ScreenshotController` handles the entire screenshot lifecycle. Currently, it suffers from several issues:
- **Loose Typing**: Data passed from QML (redactions, crop rects) is not strictly validated, leading to potential runtime errors.
- **God Method**: `saveScreenshot` performs image manipulation, path resolution, filesystem I/O, clipboard interaction, and model updates in a single block.
- **Testing Barriers**: The tight coupling to `QGuiApplication.primaryScreen()` and direct filesystem writes makes it difficult to unit test without side effects.
- **Inconsistent State**: It manually updates `self.app._categories` and model private attributes, bypassing the encapsulation established in the `OpsController` refactor.

## Scope & Impact

**In Scope:**
- Define Pydantic schemas for `Redaction` and `ScreenshotParams`.
- Extract image processing (crop/redact) into `src/skill_manager/core/image_processing.py`.
- Refactor `ScreenshotController` to delegate logic and use validated models.
- Implement 100% unit test coverage for the new image processing logic and controller.
- Create a UI/E2E test using `pytest-qt` to verify the "Capture -> Redact -> Save" flow.

**Out of Scope:**
- Changes to the QML overlay (`ScreenshotOverlay.qml`).
- Refactoring the `SynchronousTaskRunner`.

## Implementation Steps

### Phase 1: Schemas & Processing
- Create `src/skill_manager/core/image_processing.py` containing:
    - `Redaction` (Pydantic model: x, y, width, height).
    - `apply_redactions(pixmap, redactions)` function.
    - `crop_and_redact(pixmap, crop_rect, redactions)` function.
- Update `src/skill_manager/core/schemas.py` to include `ScreenshotParams`.

### Phase 2: Refactor ScreenshotController
- Update `saveScreenshot` to:
    1. Validate inputs using `Redaction.model_validate`.
    2. Use `ImageProcessor` for image manipulation.
    3. Use `app.get_active_project_storage()` (or equivalent) for path resolution.
    4. Use `app.ops.add_virtual_skill()` or `model.addOrUpdateSkills` with `SkillRecord`.

### Phase 3: Unit Testing
- Test `ImageProcessor` with various `QPixmap` sizes and redaction counts.
- Test `ScreenshotController` by mocking the `ImageProcessor` and filesystem.

### Phase 4: UI/E2E Testing
- Implement `tests/test_ui_screenshot_flow.py` to verify the signal chain and model integration.

## Verification & Rollback

- **Verification:** `pytest --cov=src/skill_manager/controllers/screenshot_controller.py`.
- **Rollback:** Standard git revert.

## Cross-references

- Workflow: [`conductor/workflow.md`](workflow.md)
- Active tracks: [`conductor/tracks.md`](tracks.md)
- ADRs: [`../ADR_INDEX.md`](../ADR_INDEX.md)
