# App Update Fixes Plan

## Approach
Fix the `AppUpdateController`'s `_sync_check_updates` method to prevent thread blocking on timeout by manually managing the `ThreadPoolExecutor`. Modify the return signature of `_sync_check_updates` to provide error details, and update `_on_updates_checked` to provide user-facing error feedback instead of incorrectly reporting "SkillManager is up to date" on failure.

## Scope
- In: `src/skill_manager/controllers/app_update_controller.py`, `tests/test_app_update_controller.py`.
- Out: Other controllers or skill update logic.

## Action Items
- [x] Task 1.1: Refactor `AppUpdateController._sync_check_updates` to return `(version, error)` tuple and use `pool.shutdown(wait=False, cancel_futures=True)`.
- [x] Task 1.2: Refactor `AppUpdateController._on_updates_checked` to accept an `error` parameter and display it to the user.
- [x] Task 1.3: Update `on_checked` wrapper in `AppUpdateController.checkForUpdates` to handle the `(version, error)` tuple.
- [x] Task 1.4: Update `tests/test_app_update_controller.py` to match the new `_sync_check_updates` tuple return type.
- [x] Task 1.5: Add/update tests in `tests/test_app_update_controller.py` to verify that errors are correctly passed to `_set_status` on manual checks.

## Validation
- Ensure all tests in `test_app_update_controller.py` pass.
- Run `ruff check` and `ruff format` to ensure linting passes.