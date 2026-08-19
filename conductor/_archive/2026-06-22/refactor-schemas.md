# Refactoring Plan: Schema Validation and Test Coverage (SDET)

> Historical refactor plan — preserved for traceability. See
> [`conductor/tracks.md`](tracks.md) for the active track record.

**Status:** Historical (completed) · **Date:** unknown

## Background & Motivation

The user requested an SDET-led refactoring focusing on strict validation boundaries (adapted to Pydantic for this Python/Qt project) and comprehensive test coverage. Analysis of `src/skill_manager/core/schemas.py` reveals loose typing and permissive validation:
- Pydantic models extensively use `extra="allow"`, negating strict boundary checks.
- Fields like `tags` and `description` accept multiple types loosely with weak coercers.
- `CacheState` performs manual iteration and parsing of `SkillRecord` instead of utilizing Pydantic's built-in recursive validation.
- Missing coverage for invalid inputs, missing fields, and boundary limits.

## Scope & Impact

**In Scope:**
- Refactor `src/skill_manager/core/schemas.py` to enforce strict validation boundaries.
- Rewrite `tests/test_schemas.py` to achieve 100% coverage on practical use cases, edge cases, error states, and validation boundaries.
- Create an E2E-style UI test script utilizing `pytest-qt` to validate the integration of schemas with the UI layer.

**Out of Scope:**
- Modifying the underlying database or persistence logic beyond schema compatibility.
- Changing `SkillRecord` property names.

## Implementation Steps

### Phase 1: Refactor `schemas.py`
- Change `extra="allow"` to `"ignore"` to prevent unknown data from polluting models, or `"forbid"` for strict boundaries.
- Improve `tags` and `description` coercers to uniformly parse lists/strings and sanitize data.
- Remove manual `_validate_skills` in `CacheState` and replace with `skills: list[SkillRecord] = Field(...)` relying on Pydantic V2 automatic validation.

### Phase 2: Unit Testing (`test_schemas.py`)
- Implement comprehensive unit tests focusing on validation boundaries (empty objects, null values, type mismatches).
- Add edge cases (e.g., extremely long strings, nested invalid metadata).
- Validate legacy migration functions like `AppConfig.from_legacy`.

### Phase 3: UI/E2E Testing
- Add a new test script using `pytest-qt` to emulate a user loading a skill package, validating that the strict `schemas.py` successfully handles and displays the skill without errors.

## Verification & Rollback

- **Verification:** Run `pytest --cov=src/skill_manager/core/schemas.py` to ensure 100% test coverage.
- **Rollback:** Revert changes via git if models introduce breaking schema incompatibilities with existing user cache files.

## Cross-references

- Workflow: [`conductor/workflow.md`](workflow.md)
- Active tracks: [`conductor/tracks.md`](tracks.md)
- ADRs: [`../ADR_INDEX.md`](../ADR_INDEX.md)
