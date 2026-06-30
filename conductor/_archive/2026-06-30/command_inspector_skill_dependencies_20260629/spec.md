# Spec — Command Inspector: Skill Dependencies pills

## Summary

Display detected skill dependencies as clickable pills in the Command
Inspector, with always-on body highlights and scroll-to-focus on click.

## Components

1. **`controllers/ops_controller.py`**
   - `getReferencedSkillsForCommand(command_path)` — returns ordered list of
     `{name, folder_name, category, local_path, occurrences}` dicts.
   - `getSkillReferenceRanges(command_path)` — returns ordered list of
     `{name, start, end}` character-offset ranges.

2. **`SkillManagerComponents/SkillReferenceOverlay.qml`**
   - Lightweight overlay that calls `TextArea.select(start, end)` on click
     and scrolls the parent `SmoothScrollView` to the first match.

3. **`SkillManagerComponents/CommandInspector.qml`**
   - New `dependencyList` / `referenceRanges` properties, updated via
     `Connections { target: AppController; onSelectedSkillChanged }`.
   - "Skill Dependencies" section with a `Flow`/`Repeater` of pill chips.
   - `SkillReferenceOverlay` anchored to the body `TextArea`.

4. **`core/diagnostics.py`**
   - New `CATEGORY_COMMAND_REFERENCED_SKILLS_RENDERED` event.

## UX Behavior

- Section is hidden when `dependencyList.length === 0`.
- Pills show `name` and `× N` badge when `occurrences > 1`.
- Click a pill: body scrolls to the first match and selects it
  (blue highlight) for 2 seconds, then clears.

## Files Changed

| File | Change |
|------|--------|
| `controllers/ops_controller.py` | Add 2 slots |
| `core/diagnostics.py` | Add 1 constant |
| `SkillManagerComponents/SkillReferenceOverlay.qml` | New file |
| `SkillManagerComponents/CommandInspector.qml` | Add properties, section, overlay |
| `SkillManagerComponents/qmldir` | Register overlay |
| `tests/test_command_referenced_skills_pills.py` | New test file |

## Test Coverage

- `TestGetReferencedSkillsForCommand` — 4 tests
- `TestGetSkillReferenceRanges` — 2 tests
- `TestCommandInspectorQML` — 3 tests
