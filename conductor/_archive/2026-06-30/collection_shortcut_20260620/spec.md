# Per-Collection Quick-Copy Shortcut

## Purpose
Allow each custom collection to have its own keyboard shortcut. Pressing the
shortcut copies the collection's skill references to the clipboard AND
auto-pastes them into whichever field the user currently has focused. This
removes the "Open QuickCopy -> pick collection -> click Copy" round-trip and
turns collections into one-keystroke text-injection templates.

## In Scope
- Optional `shortcut` (str) and `shortcut_enabled` (bool) on `CollectionConfig`.
- Settings UI in `ShortcutsSettings.qml` to assign/clear/toggle per collection.
- Dynamic `Shortcut` registrations in `Main.qml` via `Repeater`.
- Win32 Ctrl+V auto-paste using `keybd_event`.
- Auto-claim (steal) semantics: assigning a sequence frees it from any
  built-in action and any other collection.
- `Reset to Defaults` clears every collection's shortcut (and disables them).

## Out of Scope
- Global/system-wide hotkeys (in-app focus only).
- Renaming the collection edit dialog.
- Config migration tooling (Pydantic `extra="ignore"` + defaults handle it).

## Acceptance Criteria
1. User can assign a sequence to any collection from Settings -> Shortcuts.
2. Pressing the sequence (app focus) copies the collection's references and
   pastes them into the previously-focused field.
3. Attempting to bind a sequence already in use silently frees the old
   binding; status bar reports the change.
4. Per-collection `GlassSwitch` toggles enable/disable without losing the
   recorded sequence.
5. `Reset to Defaults` clears every collection's shortcut and disable flag.
6. Existing 16 static shortcut rows are unaffected.
7. `python run_tests.py` reports 0 failures and lint is clean.

## Risks
- **Focus handover** between SkillManager and the target app may flake;
  mitigate with a 50-120 ms `QTimer.singleShot` before `keybd_event`.
- **Auto-claim surprise**: a user assigning `Ctrl+C` to a collection breaks
  the built-in Copy binding; mitigated by explicit status message.
