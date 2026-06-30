# Changelog

## Unreleased

### Features
- Silent background cache refresh: all refresh paths (watcher, poll, manual button, keyboard shortcut, rebuild cache) now run entirely on background threads with no `isLoading` flicker and no status text. The app remains fully responsive during refresh.
- Cooperative in-flight refresh cancellation: a new generation counter lets a fresh refresh cancel an in-progress one, preventing stale data from overwriting newer results.
- Add 4 diagnostic categories: `CATEGORY_REFRESH_DEBOUNCED`, `CATEGORY_REFRESH_CANCELLED`, `CATEGORY_REFRESH_COMMITTED`, `CATEGORY_REFRESH_BACKGROUND_START`, `CATEGORY_CACHE_REBUILD_ASYNC`

### Refactoring
- Introduce `PreparedModelState` dataclass + `SkillModel.replacePreparedState()` to swap a fully-computed model state in a single atomic reset, replacing the previous incremental `setSkills` / `_apply_filter` calls that ran on the main thread.
- Rewrite `DiscoveryController` pipeline: heavy work (skill construction, filter pass, search-index build, row prep, visibility) runs in `_run_pipeline` on a background thread; only the final atomic commit runs on the main thread.
- `rebuildCache()` now executes asynchronously via `BackgroundTaskRunner` instead of blocking the UI.

### Bug Fixes
- Fix "Cannot create delegate / Object or context destroyed during incubation" QML warning at startup by deferring `beginResetModel`/`endResetModel` via `Qt.callLater` (one event-loop tick) so QML can process `cacheBuffer = 0` before delegates are destroyed.
- Fix filter-setter re-entrancy during incubation: `_commit_prepared_state` no longer toggles the `incubating` flag at end of commit (avoids premature queue drain); only sets `incubating = True` when the model already has skills (skips on first startup).
- Connect `onAboutToMutateStructure` / `onStructureMutated` in `QuickCopyView.qml` so `cacheBuffer` is zeroed and restored around model resets (matches `LibraryView.qml` pattern).

### Tests
- Add 5 regression tests in `test_incubation_coordination.py` for `replacePreparedState` incubation deferral (deferred-when-incubating, applied-when-empty, replayed-on-ready, replayed-on-force-end, applied-when-not-incubating).
- Update 13 test files for the new `_commit_prepared_state` / `PreparedModelState` / `FilterState` API.

### Chores
- Workspace cleanup: audit `.gitignore`, archive 24 orphan conductor plans
- Add ADR-0015 (conductor root plan archival) and ADR-0016 (`.opencode` gitignore policy)
- Add `docs/HOUSEKEEPING.md` with cleanup rules and exclusion list
- Add `metadata.json` to 7 conductor tracks missing it
- Fix `docs/ARCHITECTURE.md` CI/CD section: replace release-please reference with python-semantic-release
- Update `docs/API.md`: document package add/edit JSON return types (ADR-0013/0014)
- Update `AGENTS.md`: add housekeeping pointer and `image/TODO` exclusion
- Update `README.md`: add `docs/HOUSEKEEPING.md` to documentation table
- Update `DESIGN.md`: add ADR-0003/0004/0008 cross-links

## v1.5.0

### Features
- Add 7 diagnostic categories for app update flow (app_update_check, app_update_available, app_update_up_to_date, app_update_applied, app_update_failed, app_update_skipped_dev, tuf_client_init, tuf_bundle_validation)
- Emit structured diagnostic events across check/apply/init paths in AppUpdateController and AppUpdateService
- Add post-apply bundle version validation
- Harden progress_hook for tufup signature variants (1-arg, 2-arg, zero-arg)

### Tests
- Add test_app_update_diagnostic.py (12 cases for diagnostic event emission)
- Add test_app_update_e2e.py (6 cases with local TUF repo + HTTP server)
- Add test_app_update_progress_hook.py (5 cases for hook signature variants)
- Extend test_app_update_sdet.py (+6 cases for edge cases and error paths)

### Bug Fixes
- Fix silent dev-mode skip in checkForUpdates (now emits diagnostic event)
- Fix progress_hook crash on unexpected tufup signature

## v1.1.1

### Features
- Add tests for package storage resolution and fingerprinting functionality
- Refactor skill package management to support npx

### Bug Fixes
- Enforce package storage isolation and prevent data loss

## v1.1.0

### Features
- Add TUF release publishing script and new UI components
- Enhance error handling and update logic in AppUpdateController
- Refactor DiscoveryController for synchronous discovery
- Implement testing environment setup and enhance UI components
- Improve KeySequenceCapture keyboard accessibility
- Update README with inline video and improved formatting

### Refactoring
- Improve logging setup and clean up imports across multiple modules
- Robustify build script and add missing hidden imports

## v1.0.1

### Features
- Add LICENSE file and update authorship in pyproject.toml
- Search, categorization optimization, updating process optimization

## v1.0.0

### Features
- Release 1.0 major version
- Version bump calculator implementation
- Dual-branch release strategy

## v0.5.0

### Features
- Documentation updates and release workflow improvements

### Refactoring
- Core architecture updates

## v0.4.5

### Features
- Sentinel security fixes for path traversal vulnerabilities

## v0.4.4

### Features
- Documentation and release process updates

## v0.4.3

### Features
- Release workflow improvements

## v0.4.2-dev.3

### Features
- Implement version bump calculator and update release workflow
- Sentinel security fixes

## v0.4.0

### Features
- Release workflow migration to dynamic refs
- Documentation and process updates

## v0.3.3

### Features
- Release trigger handling improvements

## v0.3.2-dev.1

### Refactoring
- Update release trigger descriptions and handling
- Sentinel security fixes
