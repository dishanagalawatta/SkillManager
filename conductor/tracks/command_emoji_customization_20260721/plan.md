# Plan: Customizable Emoji for Commands

## Approach

Commands currently render a hardcoded `⚡` in `SkillItem.qml:297` — there is no
per-command emoji field anywhere. We add an app-side emoji **override** stored in
`config.json` (keyed by the command's `local_path`), surface it through the
`SkillModel` as a new `EmojiRole`, and let the user pick/reset the emoji from the
**Create/Edit Custom Command** dialog via a built-in QML emoji picker. Scope is
**commands only**; skills keep their category emoji.

## Scope

- In:
  - Persist per-command emoji override in `config.json` (no source-file writes).
  - New `EmojiRole` in `SkillModel`; `SkillItem.qml` shows the override (fallback `⚡`).
  - Emoji editor (button + reset) in `CommandCreateDialog.qml` for BOTH create and edit.
  - New `EmojiPicker.qml` popup (search + grid + recents).
  - `AppController` slots: `getCommandEmoji`, `setCommandEmoji`, `clearCommandEmoji`, recents.
  - Unit + contract tests; updated docs (USER_GUIDE, this plan).
- Out:
  - Emoji for skills (only commands).
  - Writing emoji into the command `.md` frontmatter.
  - Cross-machine sync of emoji.

## Action Items

- [x] 1. `core/config.py`: add `command_emoji_overrides` dict + `get/set/clear_command_emoji(local_path, emoji)` and `get/add_emoji_recent` on `ConfigManager`; add passthrough methods on `ScopedConfigManager` that hit the parent global key (not namespaced).
- [x] 2. `core/models/entities.py` + `core/schemas.py`: add `emoji: str | None = None` to `Skill` and `SkillRecord`.
- [x] 3. `core/models/qt_model.py`: add `EmojiRole`; in `data()` return override-or-`⚡` for commands, `None` otherwise; register in `roleNames()`; add `refresh_emoji_for_path(path)` that emits `dataChanged` for the matching row.
- [x] 4. `app.py`: add slots `getCommandEmoji(path)->str`, `setCommandEmoji(path, emoji)`, `clearCommandEmoji(path)`, `getEmojiRecents()->list`, `addEmojiRecent(emoji)`. `setCommandEmoji` clears when emoji in (`""`,`⚡`); otherwise stores and calls `skillModel.refresh_emoji_for_path`. Make `createCustomCommand` return the new local path (str) so the dialog can persist emoji for new commands. Add info-level logging.
- [x] 5. `SkillManagerComponents/EmojiPicker.qml` (new): `Popup` with search `TextField`, `GridView` of a curated emoji list, recents row, and `signal emojiSelected(string)`. Theme-token styling only.
- [x] 6. `dialogs/CommandCreateDialog.qml`: add `property string pendingEmoji` (default `⚡`); preload in `openForEdit` via `AppController.getCommandEmoji(skill.local_path)`, reset in `openWithContext`; add an "Emoji" row with a button showing `pendingEmoji` that opens `EmojiPicker`; on `emojiSelected` set `pendingEmoji`. On every save path (create, edit, conflict overwrite, conflict rename) persist via `AppController.setCommandEmoji(path, pendingEmoji)` (use returned path for create).
- [x] 7. `SkillManagerComponents/SkillItem.qml`: change line 297 (`if (model.isCommand) return "⚡"`) to `if (model.isCommand) return model.emoji || "⚡"`.
- [x] 8. Tests: `tests/test_*emoji*.py` — config override get/set/clear round-trip; model `EmojiRole` (command override vs default, non-command None); controller slot clears on default and refreshes; recents add/get. Add a QML contract assertion in the existing qol-contract test that command rows expose `emoji`.
- [x] 9. Validation: run `uv run ruff check src tests`, `uv run ruff format src tests`, `uv run pytest -n auto` (smoke the new file + model/controller tests).
- [x] 10. Docs: update `USER_GUIDE.md` with "Customize a command's emoji"; mark this track's plan done.

## Status: Done

## Open Questions

- None blocking. (Decisions locked: commands-only, config.json storage, built-in QML picker, editor in create/edit dialog.)
