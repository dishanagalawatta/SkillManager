# ADR-0029: Package Deletion and Local Storage Cleanup Lifecycle

> Status: **Accepted**
> Date: 2026-08-20
> Owner: @DIKKA

## Context

When removing a skill package from the Updates view (via `removeUpdatePackage`), the system previously only removed the package record from `_update_packages` and updated the configuration file.

This left behind:
1. The package's local storage directory (e.g. `~/.agent/skills/find-skills-2b87d3d3`).
2. Local git repository clones under `~/.local/share/SkillManager/package_clones/`.
3. Package lockfiles and manifests in target parent directories.
4. Persistent inventory entries in `package_skill_inventory.json` and project ownership entries in `project_skill_ownership.json`.
5. Cached skills in `cache.json` and in-memory UI models (`_library_model`, `_quick_copy_model`).
6. Active file watchers (`SkillFolderWatcher`) continuously receiving inotify events for orphaned directories on disk.

## Decision

1. **Dedicated Cleanup Engine (`delete_package_storage`)**:
   - Implemented in `core/skill_packages/storage.py` with strict safety checks (`is_safe_deletion_target`).
   - Prevents deletion of system roots (`/`, `C:\`), user home (`~`), current working directory (`CWD`), `DATA_DIR` root, active project directories (`_projects`), and user source roots (`_sources`).
   - Supports Windows read-only git object permission clearing on deletion (`_on_rmtree_error`).

2. **Dedicated vs. Shared Storage Handling**:
   - **Grouped mode**: Deletes the entire isolated package storage subdirectory (e.g. `~/.agent/skills/find-skills-2b87d3d3`).
   - **Direct mode**: Safely purges only the package's specific `managed_folders` within shared roots.

3. **Full Lifecycle Coordination**:
   - `UpdateController.removeUpdatePackage(index)` coordinates storage deletion, cache invalidation (`patch_cache_remove`), inventory/ownership cleanup, model purging (`_library_model`, `_quick_copy_model`), watcher unregistration, and update stats recalculation in a single unified operation.

## Consequences

### Positive

- Zero orphaned directories, git clones, lockfiles, or inotify events on package removal.
- Immediate UI synchronization across Library and Quick Copy models without requiring app restart.
- Comprehensive safety guards prevent accidental data loss in project roots or user directories.

### Negative

- None. Deletion is scoped to dedicated package folders and managed subdirectories.

### Neutral

- User custom source folders registered directly in `_sources` continue to be unlinked (not deleted) via `removeSource`.

## References

- `src/skill_manager/core/skill_packages/storage.py`
- `src/skill_manager/controllers/update_controller.py`
- `tests/test_package_storage.py`
- `tests/test_update_controller.py`
