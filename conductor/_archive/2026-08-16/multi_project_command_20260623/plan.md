# Plan — Multi-project command selection

> Deploy custom commands to multiple projects simultaneously.
> Fan-out copies: one `.md` per selected project's `.agents/commands/`.
> Uses existing `GlassMultiSelect` component (proven in QuickCopyView).

## Scope

- In: Command create/edit/delete dialogs, orchestrator slots, core fan-out logic, docs.
- Out: Categories (single-value), collection changes, skill folder operations.

## Action Items

- [x] Step 1: Conductor track + metadata
- [x] Step 2: Core fan-out functions (`core/commands.py`)
- [x] Step 3: Tests for core functions (`tests/test_commands.py`)
- [x] Step 4: Orchestrator slots (`controllers/ops_controller.py`, `app.py`, stubs)
- [x] Step 5: Dialog QML — GlassMultiSelect (`CommandCreateDialog.qml`)
- [x] Step 6: Inspector QML — multi-delete (`CommandInspector.qml`)
- [x] Step 7: Docs — API, user guide, ADR-0019
- [ ] Step 8: Validation — `python run_tests.py` → 0 failures, lint clean
- [x] Step 9: Skip-overwrite on identical content
  - [x] Sub-task: byte-equal content check in `update_custom_command_file`
  - [x] Sub-task: 3 new tests in `tests/test_commands.py`
  - [x] Sub-task: validate via `uv run python -m pytest tests/test_commands.py`

## Design Decisions

- **Fan-out copies (ADR-0019):** Each selected project gets its own independent `.md`.
- **`QStringList` signature:** `@Slot(str, str, "QStringList", str)` for create/update.
- **Cascade delete with toggle:** Inspector shows holder-project checklist, all pre-checked.
- **Edit pre-fill:** Opens with all holder projects pre-selected.

## Open Questions

- None — locked by user choices Q1=A, Q2=A, Q3=A, Q4=A, Q5=A (byte-equal content check).
