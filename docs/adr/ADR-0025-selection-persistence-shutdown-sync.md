# ADR-0025: Selection State Synchronization and Shutdown Persistence

> Status: **Accepted**
> Date: 2026-08-13
> Owner: @DIKKA

## Context

Users reported that SkillManager failed to remember selected items across application restarts. Investigation revealed four distinct root causes:
1. In `SelectionMixin`, active multi-selections (`_selected_ids`) were only written to `_selections_by_project` during project filter swaps (`_swap_project_selection`), causing selection changes in the current project to be omitted when serializing to disk.
2. In `SkillModel.__init__`, selection restoration required `initial_project` to be truthy (`if initial_project and initial_project in self._selections_by_project:`), which silently skipped restoring selections when `project_filter` was `""` (the default "All Projects" view).
3. During application exit (`AppController.on_quit`), pending debounced timers for selection saving (`_project_selections_save_timer`) and category collapse (`_collapse_save_timer`) were interrupted without flushing pending state changes to disk.
4. Active single-skill inspector selections (`SelectedSkillController`) were never persisted across app sessions.

## Decision

1. **Immediate In-Memory Synchronization**:
   - `SelectionMixin` implements `_sync_current_project_selection()` to immediately synchronize `_selected_ids` into `_selections_by_project[current_project]` whenever selection changes (`toggleSelection`, `setSelected`, `selectAll`, `clearSelection`, `selectByPaths`) and prior to disk serialization.
2. **Default Project Selection Restoration**:
   - `SkillModel.__init__` checks `if initial_project in self._selections_by_project:` without requiring non-empty string truthiness, restoring default (`""`) view selections on boot.
   - `initial_project` is type-guarded with `isinstance` to prevent type errors from unhashable test mock objects.
3. **Shutdown Lifecycle Timer Flushing**:
   - `AppController.on_quit()` explicitly stops and flushes all active model save timers (`_project_selections_save_timer` and `_collapse_save_timer`) for both `_library_model` and `_quick_copy_model` to disk.
4. **Inspector Selection Persistence**:
   - `SelectedSkillController` persists `last_selected_skill_path` to `ConfigManager`.
   - `DiscoveryController` restores the active skill in the inspector during model state commit on boot.

## Consequences

### Positive

- Selection state (both multi-select checkboxes and active inspector pane) is perfectly preserved across application closes and restarts.
- Eliminates race conditions where exiting within the 500ms debounce window caused lost user selections.
- Restores selection state for both all-projects view (`""`) and named project filters consistently.

### Negative

- Small additional disk write during shutdown if timers were active.

### Neutral

- `project_selections` key in config schema remains backward-compatible.

## References

- Implementation plan: [implementation_plan.md](../../.gemini/antigravity/brain/38af4f0f-37df-4e9d-b30b-1bf8e25081ba/implementation_plan.md)
- Walkthrough: [walkthrough.md](../../.gemini/antigravity/brain/38af4f0f-37df-4e9d-b30b-1bf8e25081ba/walkthrough.md)
- Tests: `tests/test_selection_persistence.py`
