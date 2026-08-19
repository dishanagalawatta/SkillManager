# Plan

Make the compact mode of the application more compact while maintaining a modern, sleek design.

## Objective
Implement the "Ultra Compact" design approach by reducing the row height to 32px to match the application's compact menus, while scaling down internal margins, icons, and typography proportionately.

## Key Files & Context
- `src/skill_manager/SkillManagerComponents/SkillItem.qml`
- `tests/test_qml_qol_contract.py`

## Implementation Steps

[x] **Step 1: Update UI Constants in `SkillItem.qml`**
   - Update `Item` and nested `height` when `compactRows` is true: `42` -> `32`.
   - Update `bg` `topMargin` and `bottomMargin`: `3` -> `2`.
   - Update Checkbox size: `18` -> `16`. Checkbox text size: `11` -> `10`.
   - Update Icon section size: `26` -> `22`. Icon text size: `14`/`16` -> `12`/`14`.
   - Update main Item Text size: `12` -> `11`.
   - Update Selection indicator height: `20` -> `16`.

[x] **Step 2: Update Unit Tests**
   - In `tests/test_qml_qol_contract.py`, update the assertion checking for `42` to expect `32` instead (`assert "root.compactRows ? 32 : 54" in skill_item`).

## Verification & Testing
- Start the application and toggle "Compact List Rows" in the settings.
- Verify that the layout remains clean, readable, and functional.
- Run the test suite (`pytest`) to ensure `test_qml_qol_contract.py` passes successfully.