# Refactoring Plan: ConfigController (SDET)

> Historical refactor plan — preserved for traceability. See
> [`conductor/tracks.md`](tracks.md) for the active track record.

**Status:** Historical (completed) · **Date:** unknown

## Background & Motivation

The `ConfigController` serves as the bridge between the UI settings and the application's configuration state. It currently handles a large number of properties and management tasks but lacks strict runtime validation for property updates. By integrating the existing `AppConfig` Pydantic model into the controller's setters, we can ensure that configuration remains valid and consistent, even when modified via dynamic UI inputs.

## Scope & Impact

**In Scope:**
- Refactor `ConfigController` to use `AppConfig` for validating configuration updates.
- Centralize property setting logic to handle validation, persistence, and signal emission.
- Harden `addSource` and `addProject` using `pathlib.Path` for better cross-platform reliability.
- Implement comprehensive unit tests in `tests/test_config_sdet.py` focusing on validation boundaries (e.g., negative intervals, invalid mode strings).
- Create `tests/test_ui_config_flow.py` (Pytest-Qt) to verify that UI-driven config changes propagate to the application state and persistence layer.

**Out of Scope:**
- Redesigning the QML settings view.
- Changes to the underlying `ConfigManager` persistence logic.

## Implementation Steps

### Phase 1: Controller Refactor
- Update property setters to validate values using `AppConfig.model_validate` (partial updates).
- Refactor `addSource` and `addProject` to use `pathlib.Path` and improved normalization.
- Simplify state synchronization between `self.app` and `self.config`.

### Phase 2: Unit Testing
- Create `tests/test_config_sdet.py`.
- Verify that invalid configuration values (e.g., non-numeric scroll speeds, invalid update modes) are handled safely without crashing.
- Verify that path normalization works as expected for both local paths and `file://` URLs.

### Phase 3: E2E UI Testing (Pytest-Qt)
- Create `tests/test_ui_config_flow.py`.
- Simulate changing settings (e.g., toggling "Auto Check Updates", changing "Scroll Speed") and verifying signals are emitted and the config is updated.

## Verification & Rollback

- **Verification:** Run `pytest tests/test_config_sdet.py tests/test_ui_config_flow.py`.
- **Rollback:** Standard git revert.

## Cross-references

- Workflow: [`conductor/workflow.md`](workflow.md)
- Active tracks: [`conductor/tracks.md`](tracks.md)
- ADRs: [`../ADR_INDEX.md`](../ADR_INDEX.md)
