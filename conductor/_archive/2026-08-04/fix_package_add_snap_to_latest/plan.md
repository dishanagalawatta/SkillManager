# Plan

On Add, snap `current_version = latest_version` so a registered package shows "Up to Date" until the registry moves. Block save with an inline error when `latest_version` cannot be auto-detected.

## Scope

- In: `addSkillPackage` path (controller, slot, QML dialog, version helper, tests, ADR).
- Out: TUF, semver-aware comparison, `updateNow` / `runPackageUpdate` logic, startup migration, schema changes.

## Action Items

[x] Step 1: Add `sync_current_to_latest` param to `check_skill_package_versions` in `core/skill_packages/versioning.py:146`; extract existing "post-update sync" block (lines 204-210) into a helper.
[x] Step 2: Update `addSkillPackage` in `controllers/update_controller.py:250` to two-phase call (detect, then snap) and return `{"ok", "error", "name"}`; refuse to append on empty `latest_version`.
[x] Step 3: Change `AppController.addSkillPackage` slot in `app.py:835` to `@Slot(dict, result=str)`, return orjson dict.
[x] Step 4: Update `PackageEditDialog.qml:656-680` Create-button handler to read return value; show `saveError` inline; keep dialog open on failure.
[x] Step 5: Add unit tests for `sync_current_to_latest` + undetectable-latest block.
[x] Step 6: Add ADR-0013 to `ADR_INDEX.md`.
[x] Step 7: `uv run ruff check .` + `uv run pytest` + `python run_tests.py` — all green.

## Completion Notes

- Steps 1–5 were implemented in commit `d539627` (2026-06-22) and
  verified in place on 2026-08-04.
- Step 6: `ADR-0013-package-add-snap-to-latest.md` created and indexed;
  ADR-0014 (edit path) created in the same pass.
- Step 7: gates re-run on 2026-08-04 — `uv run ruff check src tests` clean;
  full suite `uv run pytest -n auto --dist loadfile` → 1674 passed,
  1 skipped, 1 environmental flake (`inotify instance limit reached` under
  parallel watchdog observers; passes in isolation). `run_tests.py` does not
  exist in the repo — gates run via `uv run pytest` (canonical per AGENTS.md).

## Open Questions

- None.
