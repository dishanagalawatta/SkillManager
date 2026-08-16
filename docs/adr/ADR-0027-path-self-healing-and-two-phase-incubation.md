# ADR-0027: Storage Path Self-Healing Normalization and Two-Phase Model Incubation

> Status: **Accepted**
> Date: 2026-08-17
> Owner: @DIKKA

## Context

1. **Storage Path Duplication & Missing Leading Slashes**:
   When package paths were stored in `config.json` without a leading slash (e.g., `"home/user/.agent/skills"`), `Path(os.path.expanduser(configured)).resolve()` resolved relative to the process working directory, duplicating path segments (e.g., `/home/user/home/user/...`). Watchdog monitors registered these non-existent paths, causing duplicate scanning errors and filesystem event failure.

2. **QML Model Incubation Race & 5.0-Second Queue Deadlock**:
   Previously, `DiscoveryController._commit_prepared_state()` manually set `incubating = True` on both models before invoking `replacePreparedState()`. This caused `replacePreparedState()` to defer its own state replacement onto `_pending_signals` while `_all_skills` was non-empty, deadlocking the model until the 5.0-second safety timer expired. Furthermore, when views were toggled during live model updates, in-flight QML delegate incubations were destroyed mid-flight (`Object or context destroyed during incubation`).

## Decision

1. **Self-Healing Path Normalization**:
   - Enhance `repair_malformed_path()` in `src/skill_manager/core/copier.py` to unconditionally detect missing leading slashes on standard Unix root prefixes (`home/`, `tmp/`, `var/`, `usr/`, `etc/`) and strip nested root patterns across Unix and Windows paths (`C:\...`).
   - Run `_normalize_paths_on_startup()` in `AppController` on application boot to automatically clean and persist normalized paths across `projects`, `sources`, and `_update_packages` before filesystem watchers and discovery services initialize.
   - Proactively sanitize paths in `resolve_package_storage()` and `normalize_skill_package_config()`.

2. **Two-Phase Deferred Model Incubation Protocol**:
   - Remove manual `incubating = True` forcing from `DiscoveryController`.
   - Implement a strict 2-phase deferred model reset in `SkillModel.replacePreparedState()`:
     1. Emit `aboutToMutateStructure` to notify QML views to zero `cacheBuffer = 0`.
     2. Schedule `QTimer.singleShot(0, _do_reset)` to defer `beginResetModel()`/`endResetModel()` by 1 event loop tick, allowing in-flight Qt incubators to finish or abort safely.
     3. Emit `structureMutated` to restore normal cache buffering.
   - Connect `onRowsAboutToBeRemoved` and `onRowsAboutToBeInserted` in QML views (`QuickCopyView.qml`, `LibraryView.qml`) to ensure `cacheBuffer = 0` during all granular row mutations.

## Consequences

### Positive
- Prevents invalid duplicate watchdog watcher registrations and self-heals legacy configuration entries without user intervention.
- Eliminates the 5.0-second UI stall during discovery state application.
- Prevents QML delegate destruction runtime warnings during active background scans and view switching.

### Negative
- Initial model reset requires a 1-tick `QTimer.singleShot(0)` delay, which is imperceptible to users (<1ms) but requires asynchronous signal sequencing.

### Neutral
- Legacy configurations with missing slashes are silently updated and saved to `config.json`.

## References
- [`docs/ARCHITECTURE.md`](../ARCHITECTURE.md) (Section 9 & 10)
- [`src/skill_manager/core/copier.py`](../../src/skill_manager/core/copier.py)
- [`src/skill_manager/core/models/incubation.py`](../../src/skill_manager/core/models/incubation.py)
- [`src/skill_manager/controllers/discovery_controller.py`](../../src/skill_manager/controllers/discovery_controller.py)
