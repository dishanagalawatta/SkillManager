# Plan

Implement robust check and auto-update features for Skill Packages using open-source libraries `GitPython` and `APScheduler`. This will ensure skills stay synchronized automatically without manual intervention, while offering users configurable control.

## Scope

- In:
  - Add `GitPython` and `APScheduler` as dependencies.
  - Refactor `skill_manager.core.skill_packages` (e.g., `updater.py`, `versioning.py`) to use `GitPython` instead of `subprocess` for all git operations.
  - Implement an `APScheduler` job in `app.py` to trigger on startup (and optionally periodically if configured) to run `UpdateController.scanForUpdates`.
  - Add new configuration options for skill packages (`skill_package_auto_update`, `skill_package_auto_update_mode` -> "silent" or "prompt").
  - Update `SettingsView.qml` to include Skill Package auto-update settings.
- Out:
  - Modifying the Application Update flow (`tufup` / `AppUpdateController`).

## Action Items

- [x] Task 1.1: Add `GitPython` and `APScheduler` to dependencies.
- [x] Task 1.2: Add new properties to `AppConfig` in `schemas.py` (`skill_package_auto_update: bool = True`, `skill_package_auto_update_mode: str = "prompt"`).
- [x] Task 1.3: Update `config_controller.py` to expose these new properties to QML.
- [x] Task 1.4: Update `SettingsView.qml` to display the new Skill Package update toggles.
- [x] Task 2.1: Refactor `src/skill_manager/core/skill_packages/versioning.py` to use `git.Repo` and `git.cmd.Git` (from `GitPython`) for detecting remotes and fetching tags, replacing subprocess calls.
- [x] Task 2.2: Refactor `src/skill_manager/core/skill_packages/updater.py` (`_run_git_package_update`) to perform clone and pull operations using `GitPython`.
- [x] Task 3.1: Integrate `APScheduler` (using `QtScheduler`) in `app.py` or a dedicated scheduler manager.
- [x] Task 3.2: Configure the scheduler to run `UpdateController.scanForUpdates` on application startup, and if the mode is "silent", automatically invoke `UpdateController.updateNow()`. If "prompt", notify the user.
- [x] Task 4.1: Test the `GitPython` refactor using existing or new unit tests to ensure pulling and tagging work correctly.
- [x] Task 4.2: Verify that `APScheduler` triggers the update scan properly on startup.

## Validation

- Ensure `pytest` runs and passes successfully.
- Verify through the UI that changing "Skill Package Auto Updates" persists in config.
- Verify log files that `APScheduler` starts and triggers the job.
- Verify skill packages update correctly via `GitPython`.
