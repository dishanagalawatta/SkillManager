# Refactoring Plan: DiscoveryController (SDET)

> Historical refactor plan — preserved for traceability. See
> [`conductor/tracks.md`](tracks.md) for the active track record.

**Status:** Historical (completed) · **Date:** unknown

## Background & Motivation

The `DiscoveryController` manages background skill discovery and cache synchronization. It currently uses loose dictionary typing and a positional-argument signal that is brittle and lacks strict validation. Refactoring to use Pydantic models will improve type safety, simplify incremental updates, and make the discovery process more robust.

## Scope & Impact

**In Scope:**
- Refactor `DiscoveryController` to use `CacheState` and `SkillRecord` Pydantic models.
- Simplify the internal signal signature to use a single `CacheState` object.
- Encapsulate incremental update logic (diffing) using Pydantic models.
- Implement comprehensive unit tests in `tests/test_discovery_sdet.py`.
- Implement a `pytest-qt` E2E test in `tests/test_ui_discovery_flow.py`.

**Out of Scope:**
- Changes to the core `DiscoveryService` logic (only the interface and data handling in the controller).
- Frontend (QML) changes.

## Implementation Steps

### Phase 1: Controller Refactor
- Update `DiscoveryController` to use `CacheState` for signals.
- Update `_run_discovery_sync` to validate results through `CacheState`.
- Update `_finalize_loading` to handle `CacheState` and use `SkillRecord` for incremental diffing.

### Phase 2: Unit Testing
- Mock `DiscoveryService` and verify `DiscoveryController` handles:
    - Initial discovery.
    - Cache hits via `cache_callback`.
    - Incremental updates (added/updated/removed skills).
    - Error handling.

### Phase 3: E2E UI Testing (Pytest-Qt)
- Create `tests/test_ui_discovery_flow.py`.
- Verify that calling `loadInitialData` correctly updates the `SkillModel` and UI state signals.

## Verification & Rollback

- **Verification:** Run `pytest tests/test_discovery_sdet.py tests/test_ui_discovery_flow.py`.
- **Rollback:** Standard git revert.

## Cross-references

- Workflow: [`conductor/workflow.md`](workflow.md)
- Active tracks: [`conductor/tracks.md`](tracks.md)
- ADRs: [`../ADR_INDEX.md`](../ADR_INDEX.md)
