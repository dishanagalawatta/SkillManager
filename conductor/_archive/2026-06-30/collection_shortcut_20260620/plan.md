# Plan
Per-collection keyboard shortcut. Pressing it copies the collection's skill
references to the clipboard and auto-pastes into the focused field. Built-in
shortcut conflicts auto-claim (steal). UI: new section under the static list
in `ShortcutsSettings.qml`. `Reset to Defaults` also clears every collection's
shortcut.

## Scope
- In: `core/schemas.py`, `controllers/config_controller.py`,
  `controllers/ops_controller.py`, `utils/win32.py`,
  `SkillManagerComponents/Main.qml`, `views/ShortcutsSettings.qml`,
  `tests/test_config_controller.py`, `tests/test_ops_controller.py`,
  `tests/test_qml_comprehensive_diagnostic.py`,
  `docs/USER_GUIDE.md`
- Out: `core/global_hotkey.py` (no global pynput for collections), any new
  dialog, schema migration tooling

## Action Items

### Phase 1: Schema + Controller

- [x] Task 1.1: Add `shortcut: str = ""` and `shortcut_enabled: bool = True` to `CollectionConfig` in `core/schemas.py:121`
- [x] Task 1.2: Add `_claim_sequence(self, seq, owner_name)` helper in `ConfigController` (frees built-in + other collection; emits the two signals once)
- [x] Task 1.3: Add `setCollectionShortcut(name, seq)`, `setCollectionShortcutEnabled(name, bool)`, `getCollectionShortcut(name)`, `getCollectionShortcutEnabled(name)`, `clearAllCollectionShortcuts()` to `ConfigController`
- [x] Task 1.4: Extend `resetShortcuts` to also call `clearAllCollectionShortcuts()`

### Phase 2: Copy + Win32 paste

- [x] Task 2.1: Add `send_paste_to_focused_window()` to `utils/win32.py` using `ctypes.windll.user32.keybd_event` for `Ctrl+V`; wrap in try/except
- [x] Task 2.2: Add `copyCollectionToClipboard(name)` slot in `OpsController` (resolves refs via `format_project_skill_reference`, sets clipboard, calls minimize, schedules paste via `QTimer.singleShot(50-120ms, send_paste_to_focused_window)`)
- [x] Task 2.3: Surface the slot through `AppController` in `app.py` (parallel to `copySelectedSkillsToClipboard`)

### Phase 3: QML — dynamic Shortcut + Settings UI

- [x] Task 3.1: Add `Repeater { model: AppController.customCollections; delegate: Shortcut { ... } }` to `Main.qml` after the static Shortcut block (~line 154)
- [x] Task 3.2: Add a second `GlassPill` "Collection Shortcuts" in `views/ShortcutsSettings.qml` below the static grid with header + `Repeater` of `KeySequenceCapture` + `GlassSwitch` rows
- [x] Task 3.3: Wire `onSequenceCaptured` -> `AppController.config_controller.setCollectionShortcut(name, seq)`; `GlassSwitch.onCheckedChanged` -> `setCollectionShortcutEnabled`

### Phase 4: Tests + Docs + Verification

- [x] Task 4.1: `test_set_collection_shortcut_saves` — round-trip persists
- [x] Task 4.2: `test_set_collection_shortcut_auto_claims_built_in` — assigning `Ctrl+C` clears the built-in
- [x] Task 4.3: `test_set_collection_shortcut_auto_claims_other_collection`
- [x] Task 4.4: `test_set_collection_shortcut_noop_when_unchanged`
- [x] Task 4.5: `test_set_collection_shortcut_enabled_toggles_flag`
- [x] Task 4.6: `test_reset_shortcuts_clears_collection_shortcuts`
- [x] Task 4.7: `test_copy_collection_to_clipboard_writes_references_and_schedules_paste` in `tests/test_ops_controller.py` (monkeypatch `send_paste_to_focused_window` and the timer)
- [x] Task 4.8: Update `docs/USER_GUIDE.md` shortcut table + new note on auto-paste
- [x] Task 4.9: Run `python run_tests.py` — confirm 0 failures and lint clean

### Phase 5: QML Repeater → Instantiator fix

- [x] Task 4.10: Fix `Main.qml:156-166` — swap `Repeater` to `Instantiator` (add `import QtQml`); `Repeater` requires `Item` delegates, but `Shortcut` is `QObject`-based
- [x] Task 4.11: Add 3 regression tests to `tests/test_qml_comprehensive_diagnostic.py`:
  - `test_main_qml_no_non_item_delegate_warnings` — loads Main.qml, asserts no "Delegate must be of Item type" warnings
  - `test_collection_shortcut_instantiator_creates_shortcuts` — finds `QQmlInstantiator` via `findChildren`, verifies it created Shortcut delegates
  - `test_collection_shortcut_fires_copy_collection_to_clipboard` — finds instantiated Shortcut, emits `activated()`, asserts `copyCollectionToClipboard` called with collection name
- [x] Task 4.12: Full test suite — 991/991 pass, lint clean

## Open Questions
- None remaining
