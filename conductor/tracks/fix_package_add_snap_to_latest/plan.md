# Plan

On Add, snap `current_version = latest_version` so a registered package shows "Up to Date" until the registry moves. Block save with an inline error when `latest_version` cannot be auto-detected.

## Scope

- In: `addSkillPackage` path (controller, slot, QML dialog, version helper, tests, ADR).
- Out: TUF, semver-aware comparison, `updateNow` / `runPackageUpdate` logic, startup migration, schema changes.

## Action Items

[~] Step 1: Add `sync_current_to_latest` param to `check_skill_package_versions` in `core/skill_packages/versioning.py:146`; extract existing "post-update sync" block (lines 204-210) into a helper.
[ ] Step 2: Update `addSkillPackage` in `controllers/update_controller.py:250` to two-phase call (detect, then snap) and return `{"ok", "error", "name"}`; refuse to append on empty `latest_version`.
[ ] Step 3: Change `AppController.addSkillPackage` slot in `app.py:835` to `@Slot(dict, result=str)`, return orjson dict.
[ ] Step 4: Update `PackageEditDialog.qml:656-680` Create-button handler to read return value; show `saveError` inline; keep dialog open on failure.
[ ] Step 5: Add unit tests for `sync_current_to_latest` + undetectable-latest block.
[ ] Step 6: Add ADR-0013 to `ADR_INDEX.md`.
[ ] Step 7: `uv run ruff check .` + `uv run pytest` + `python run_tests.py` — all green.

## Open Questions

- None.
