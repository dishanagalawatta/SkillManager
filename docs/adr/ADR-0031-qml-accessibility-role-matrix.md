# ADR-0031: QML Accessibility Role Matrix and Keyboard Contract

> Status: **Accepted**
> Date: 2026-09-06
> Owner: @DIKKA

## Context

PR #275 fixed `GlassToggleButton` (a `Button{checkable:true}`) announcing as a generic
`Accessible.Button` with no state, leaving screen-reader users unable to tell toggles apart
from momentary buttons. A codebase-wide audit found the same defect class in ~20 locations:
expand/collapse headers, star/archive toggles, nav active states, and select-all checkboxes —
plus missing `onPressAction`/`onToggleAction` handlers (Qt advertises an AT action only when
the handler is connected), keyboard-inoperable `MouseArea`-only surfaces, and empty
`Accessible.name` nodes. Two agent-produced regressions during the fix (since corrected)
proved the need for a recorded contract: `visualFocus` on a bare `Item` and the
`Accessible.Tab` / `Accessible.Menu` role names do not exist in this Qt build and fail
`test_qml_comprehensive_diagnostic.py` with `Unable to assign [undefined]` warnings.

## Decision

1. **Role matrix** (AT `checked` must equal click-toggles-off, never bare visual highlight):
   | Behavior | Role | Extras |
   |---|---|---|
   | Persistent on/off toggle | `Accessible.CheckBox` | `checkable`, `checked`, both handlers |
   | Mutually-exclusive tab / view switch | `Accessible.PageTab` | `checkable`, `checked`, both handlers |
   | Single-choice format list | `RadioButton` | group exclusivity documented |
   | Momentary button, ComboBox, Slider, EditableText | native role | `onPressAction` only |
2. **Every toggle wires BOTH `Accessible.onPressAction` and `Accessible.onToggleAction`**
   to the same slot as click.
3. **Focus-property rule**: `visualFocus`/`hovered` are `Control`/`HoverHandler`-only;
   `Item`/`Rectangle`/`MouseArea` targets use `activeFocus`/`containsMouse`.
4. **Names never empty**: fallback `tooltipText || iconText || labelText || text`;
   tooltips surface on keyboard focus, not hover alone.
5. **Contract tests pin roles**: an intentional role change updates the test
   (as `test_library_inspector_overlay.py:177` was updated `Button` → `CheckBox`);
   a red role assertion is never "fixed" by reverting the QML.

## Consequences

### Positive

- Screen readers announce toggle state everywhere (select, star, archive, expanders, tabs).
- Full keyboard operation: list rows, checkboxes, delete reveal, inspectors, canvas ops.
- Diagnostic suite (zero QML warnings) gates the focus-property rule automatically.

### Negative

- `test_library_inspector_overlay.py` and any future role-pinning test must be maintained
  alongside intentional role changes.
- `Accessible.Switch` is unavailable until PySide6 ≥ 6.11; `CheckBox` covers switches.

### Neutral

- No visual or behavioral delta: all changes are AT props, handlers, focus rings, and
  tooltip-focus surfacing (verified via real-app screenshots for list/settings views).

## Alternatives Considered

### Keep `Accessible.Button` on toggles, expose state via `description`

Rejected: screen readers announce no state for `Button`; `description` duplicating state
reintroduces the PR #221 double-announcement defect.

### Use `Accessible.Switch` for on/off toggles

Rejected: `Switch` role exists only since Qt 6.11 (verified against `qaccessible_base.h`);
minimum supported PySide6 predates it. Revisit when the floor is raised.

## References

- PR #275 (GlassToggleButton `Button` → `CheckBox`) — merged 2026-09-06
- Qt 6.11 `QAccessible::Role`, `Accessible` QML type, `AbstractButton.checkable` docs
- `DESIGN.md` § Accessibility; `AGENTS.md` QML UI Conventions
