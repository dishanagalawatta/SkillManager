# Plan: Refactor ImageInspectorController (SDET)

> Historical refactor plan — preserved for traceability. See
> [`conductor/tracks.md`](tracks.md) for the active track record.

**Status:** Historical (completed) · **Date:** unknown

## Background & Motivation

Refactor `ImageInspectorController` to use Pydantic models for annotation validation and extract drawing logic into a decoupled `AnnotationEngine`.

## Scope & Impact

- **In:** `src/skill_manager/controllers/image_inspector_controller.py`, `src/skill_manager/core/schemas.py`, new `src/skill_manager/core/annotations.py`.
- **Out:** QML changes, other controllers.

## Implementation Steps

- [ ] Discovery: Run coverage on `tests/test_image_inspector_color_isolation.py`.
- [ ] Schema: Define `Annotation` models (Rect, Arrow, Redact, Freehand, Text, Highlight) in `schemas.py`.
- [ ] Implementation: Create `AnnotationEngine` in `core/annotations.py` to handle `QPainter` logic.
- [ ] Implementation: Refactor `ImageInspectorController` to validate input via Pydantic and delegate to `AnnotationEngine`.
- [ ] Validation: Implement unit tests in `tests/test_image_inspector_sdet.py` with 100% coverage.
- [ ] Validation: Implement E2E UI test in `tests/test_ui_image_inspector_flow.py` (pytest-qt).

## Verification & Rollback

- **Verification:** Run `pytest tests/test_image_inspector_sdet.py tests/test_ui_image_inspector_flow.py`.
- **Rollback:** Standard git revert.

## Cross-references

- Workflow: [`conductor/workflow.md`](workflow.md)
- Active tracks: [`conductor/tracks.md`](tracks.md)
- ADRs: [`../ADR_INDEX.md`](../ADR_INDEX.md)
