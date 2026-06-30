# Auto Update via Tufup

## Approach
Implement robust background update checks and auto-updating using `tufup` (The Update Framework). The TUF repository metadata and patches will be hosted on a `gh-pages` branch. The app will support checking on startup, checking periodically, and automatically downloading updates based on user settings.

## Scope
- **In**: 
  - Integrating `tufup` into `AppUpdateController`.
  - Adding `auto_check_updates`, `auto_download_updates`, and `update_check_interval_hours` to `AppConfig`.
  - Implementing periodic background update checks using QTimer/asyncio.
  - Adding settings UI for the new update configuration.
  - Creating a script/workflow template for publishing TUF releases.
- **Out**: 
  - Rewriting the main installer framework (Inno Setup remains for initial installs).

## Action Items
- [x] Task 1.1: Add `tufup` dependency to `pyproject.toml` / `uv.lock`.
- [x] Task 1.2: Update `AppConfig`, `ConfigController`, and UI Settings to support `auto_check_updates`, `auto_download_updates`, and `update_check_interval_hours`.
- [x] Task 1.3: Refactor `AppUpdateController` to use `tufup.client.Client` instead of manual `httpx` GitHub API checks.
- [x] Task 1.4: Implement periodic checking logic (QTimer or asyncio loop) that triggers `AppUpdateController` checks in the background.
- [x] Task 1.5: Implement the update download and application logic using `tufup`'s apply capabilities.
- [x] Task 1.6: Create `scripts/publish_tuf_release.py` or a GitHub Actions workflow to automate the `tufup` repo creation and push to `gh-pages`.
- [x] Task 1.7: Test end-to-end update flow locally.

## Validation
- Verify the app correctly detects a new version from a local TUF repo test server.
- Verify periodic check triggers at the specified interval.
- Verify settings toggle correctly enables/disables background checks.