# Plan — Command Inspector: Skill Dependencies pills

## Step 1: Backend Slots (ops_controller.py)
- [x] Add `CATEGORY_COMMAND_REFERENCED_SKILLS_RENDERED` to `diagnostics.py`
- [x] Import new category in `ops_controller.py`
- [x] Implement `getReferencedSkillsForCommand(command_path)` slot
- [x] Implement `getSkillReferenceRanges(command_path)` slot

## Step 2: QML Components
- [x] Create `SkillReferenceOverlay.qml` (selection-based highlight)
- [x] Register `SkillReferenceOverlay` in `qmldir`
- [x] Add `dependencyList` and `referenceRanges` properties to `CommandInspector.qml`
- [x] Add `Connections` block to update lists on `selectedSkillChanged`
- [x] Add "Skill Dependencies" section with pill `Repeater`
- [x] Place overlay inside Command Details Rectangle

## Step 3: Tests
- [x] `test_command_referenced_skills_pills.py` — 9 tests
- [x] All existing tests pass (23 + 15 = 38)

## Step 4: Documentation
- [x] Create conductor track `spec.md`, `plan.md`, `metadata.json`

## Validation
- [x] `uv run pytest tests/test_skill_references.py` — 23 passed
- [x] `uv run pytest tests/test_qml_command_inspector_refresh.py` — 15 passed
- [x] `uv run pytest tests/test_command_referenced_skills_pills.py` — 9 passed
