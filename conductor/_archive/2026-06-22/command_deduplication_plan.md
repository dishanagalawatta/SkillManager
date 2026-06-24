# Command and Screenshot Deduplication Plan

> Historical plan — preserved for traceability. See
> [`conductor/tracks.md`](tracks.md) for the active track record.

**Status:** Historical (completed) · **Date:** unknown

## Objective

Fix the issue where custom commands and screenshots are duplicated in the skill list when multiple skill folders share the same project root.

## Background

The `DiscoveryService` scans each configured skill folder. For each folder, it also scans for "special" items:
1.  **Screenshots:** Scanned in `{project_root}/.agents/screenshots` during the folder scan.
2.  **Commands:** Scanned in `{project_root}/.agents/commands` after all folder scans.

If a project has multiple skill folders (e.g., `Repo/skills/web` and `Repo/skills/python`), they share the same `{project_root}` (`Repo`). Consequently, the same screenshots and commands are scanned and added to the list multiple times.

## Scope

- **In:** `src/skill_manager/core/discovery.py`, `src/skill_manager/core/quick_copy.py`.
- **Out:** Other components.

## Action Items

### Phase 1: Investigation & Reproductions
[ ] Step 1.1: Create a unit test `tests/test_discovery_duplication.py` that mocks a multi-folder project structure and verifies the duplication.

### Phase 2: Refactoring Discovery
[ ] Step 2.1: Remove screenshot scanning from `_scan_single_project` in `src/skill_manager/core/discovery.py`.
[ ] Step 2.2: Refactor `DiscoveryService.discover_all` to deduplicate command and screenshot scanning by project root.
[ ] Step 2.3: Remove screenshot scanning from `discover_single_project` in `src/skill_manager/core/quick_copy.py`.

### Phase 3: Validation
[ ] Step 3.1: Run the new duplication test to verify the fix.
[ ] Step 3.2: Run all existing discovery and model tests (`tests/test_discovery.py`, `tests/test_core_models_logic.py`).
[ ] Step 3.3: Run `ruff check .` and fix any linting issues.

## Verification

- **Unit Test**: `tests/test_discovery_duplication.py` will specifically target this scenario.
- **Manual Verification**: Run the app and verify that commands and screenshots appear only once even if multiple folders are added from the same repo.

## Cross-references

- Workflow: [`conductor/workflow.md`](workflow.md)
- Active tracks: [`conductor/tracks.md`](tracks.md)
- ADRs: [`../ADR_INDEX.md`](../ADR_INDEX.md)
