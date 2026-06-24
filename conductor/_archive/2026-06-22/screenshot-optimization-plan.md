# Plan: Screenshot Model Injection

> Historical plan — preserved for traceability. See
> [`conductor/tracks.md`](tracks.md) for the active track record.

**Status:** Historical (completed) · **Date:** unknown

## Objective

Inject the newly created screenshot directly into the application's models rather than triggering a full filesystem discovery scan, providing an immediate UI update.

## Scope

- **In:** Modifying `src/skill_manager/controllers/screenshot_controller.py` to construct a virtual skill dictionary for the screenshot and appending it to `_library_model` and `_quick_copy_model` via `addOrUpdateSkills`.
- **Out:** Other skill discovery workflows, full rewrite of the screenshot capture mechanism.

## Action Items

- [x] Step 1: Implementation - Update `ScreenshotController.saveScreenshot`. Keep track of the selected `project` value (`matched_project`) during path resolution.
- [x] Step 2: Implementation - Replace `self.app.refreshSkills()` with the creation of a `skill_data` dictionary matching the screenshot format used by `discover_project_skills`.
- [x] Step 3: Implementation - Call `self.app._library_model.addOrUpdateSkills([skill_data])` and `self.app._quick_copy_model.addOrUpdateSkills([skill_data])` to inject the item immediately.
- [x] Step 4: Validation/Testing - Run tests to ensure screenshot capture and display workflow doesn't break.
- [x] Step 5: Rollout/Commit - Commit the change.

## Verification

- Run `python run_tests.py` to confirm 0 failures and lint clean.

## Cross-references

- Workflow: [`conductor/workflow.md`](workflow.md)
- Active tracks: [`conductor/tracks.md`](tracks.md)
- ADRs: [`../ADR_INDEX.md`](../ADR_INDEX.md)
