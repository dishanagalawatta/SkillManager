# ADR-0035: Single-Tab-Stop Rows in GlassMultiSelect

> Status: **Accepted**
> Date: 2026-09-12
> Owner: @DIKKA

## Context

`GlassMultiSelect` rows paired a keyboard-accessible `GlassCheckBox`
with a mouse-only full-row `MouseArea` overlay. Making the row itself
focusable the naive way yields two Tab stops performing the identical
toggle (row + inner checkbox): tab-stop bloat, double screen-reader
announcement, and competing focus rings. This setup was explicitly
deferred during the PR #278/#280 consolidation pending a design choice.

## Decision

1. **Roving single stop**: each row `Rectangle` (select-all + item
   delegates) is the one `activeFocusOnTab` stop and carries the full
   ADR-0031 `CheckBox` contract (`checkable`, `checked`, both
   `onPressAction`/`onToggleAction` wired to the inner checkbox's
   `toggled()` slot, so behavior has a single source).
2. **Inner checkboxes leave the tab order**
   (`activeFocusOnTab: false` on the instances; the shared component is
   unchanged) but keep mouse visuals; row clicks also move focus to the
   row so mouse and keyboard states never diverge.
3. **Keyboard**: `Space`/`Return`/`Enter` toggle; anything else is
   declined (`event.accepted = false`) to preserve list navigation.
4. **Focus visibility**: accent border on `activeFocus`, sharing no
   channel with the hover fill.
5. **AT naming**: select-all announces
   `"Select/Deselect all, <allLabel>"`; items announce
   `"Select/Deselect <value>"`, with `checked` bound to selection state.
6. **Programmatic hooks**: `openPopup()` + `focusRow(idx)` (`-1` targets
   the select-all row) for services and verification scripts that cannot
   inject key events.

## Consequences

### Positive

- One Tab stop per row with a large focus target and full-row AT naming.
- No behavior fork: row, keyboard, and AT actions all funnel into the
  existing `toggled()` slots.
- Verified via real-app screenshot (QuickCopy editor popup, focused
  row ring, no clipping).

### Negative

- One extra Tab stop per row versus checkbox-only (accepted: the row is
  now the control, so the stop count is honest).
- `openPopup()`/`focusRow()` are small service seams on production QML.

### Neutral

- No model, selection-semantics, or component-API changes; hosts
  (QuickCopy, CommandCreate/Delete dialogs) untouched.

## Alternatives Considered

### Checkbox-only tab stops, rows mouse-only

Rejected: leaves the audited gap open — row background clickable for
mouse but unreachable by keyboard, inconsistent targets per modality.

## References

- ADR-0031 (role matrix), ADR-0034 (focus-restore precedent)
- `tests/qml/test_qml_multiselect_row_contract.py`
- `scripts/verify_multiselect_row_focus.py` (+ capture)
