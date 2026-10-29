# Plan: In-app application update download and install

## Approach

App-release checks currently stop at a toast whose "View Release" action hands the
URL to `QDesktopServices.openUrl` with no error handling. PyInstaller/AppImage
runtimes poison `LD_LIBRARY_PATH`, which breaks the `gio`/`xdg-open` helper chain,
and the failure is invisible. Add a platform-aware external URL launcher, extend
the GitHub release payload with assets, and add a verified download + platform
installer pipeline (AppImage replace, `.deb` via pkexec, Windows Inno Setup) with
a single "Download & Install" action.

## Scope

- In: `core/release_check_service.py`, new `core/app_update_service.py`, new
  `utils/external_url.py`, `controllers/app_update_controller.py`,
  `core/schemas.py`, `UpdateToast.qml`, `SettingsView.qml`, new
  `AppUpdateCard.qml`, `UpdatesView.qml`, tests, ADR/docs.
- Out: unattended/silent background updates (always explicit consent), delta
  updates, code signing.

## Action Items

- [x] Task 1.1: Add release asset metadata + platform asset selection + SHA256SUMS parsing to the release service.
- [x] Task 1.2: Add `utils/external_url.py` with sanitized `gio`/`xdg-open` launch and `QDesktopServices` fallback.
- [x] Task 1.3: Add `core/app_update_service.py` (download, checksum verification, install kind detection, installer helpers).
- [x] Task 1.4: Extend `AppUpdateState` and `AppUpdateController` with download progress, install, cancel and reliable release-page actions.
- [x] Task 1.5: Build `AppUpdateCard.qml` and wire it into Settings and the Updates view; add Update Now / View Release to `UpdateToast`.
- [x] Task 1.6: Update existing tests and add unit/QML contract tests for every new branch.
- [x] Task 1.7: Write ADR-0050 and update ARCHITECTURE / INSTALL / USER_GUIDE diagrams and text.
- [x] Task 1.8: Run ruff + focused and full test suites.
- [x] Task 1.9: Validate the real running app (Settings + Updates view screenshots).

## Notes

- Root cause evidence: `gio` under `/opt/SkillManager/_internal` in
  `LD_LIBRARY_PATH` fails with `undefined symbol: g_unix_mount_entry_get_options`;
  `xdg-open` delegates to `gio` on GNOME, so the launch can silently no-op.
- Downloads are verified against the release `SHA256SUMS`; a missing manifest
  refuses self-install (unlike the shell installer, which only warns).
- Linux `.deb` installs use graphical polkit (`pkexec`); no silent root escalation.
