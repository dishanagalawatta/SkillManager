# Plan: Drop TUF Auto-Update, Add GitHub Releases API Version Check (v1.6.0)

## Goal

Remove the entire TUF-based self-update system (server + client). Replace the
`AppUpdateController`'s "Check for Updates" / "Update Now" UX with a minimal
GitHub Releases API check that:
- Shows the user whether a newer version exists
- Provides a button to open the GitHub Releases page (where they download the
  new `.exe` / `.zip` manually)
- Performs no in-app download or install

## Architectural Decision (ADR-0010)

**Status:** Accepted, 2026

**Context.** The TUF self-update system creates a ~320 MB tar.gz bundle
(`SkillManager-1.5.4.tar.gz`) from the PyInstaller output. This file exceeds
GitHub Pages' 100 MB file size limit, blocking the `gh-pages` deploy step
(Release workflow run `27812859185`).

We considered four alternatives:
1. **Git LFS on `gh-pages`** — `raw.githubusercontent.com` returns LFS *pointer*
   files, not content, so the tufup client cannot download real bytes.
2. **Custom URL routing** (Cloudflare Worker, etc.) — adds infrastructure not
   justified for a single-platform Windows app.
3. **Subclass `tufup.Client` to rewrite URLs** — works but adds maintenance
   burden for a security-critical code path.
4. **Drop TUF, use GitHub Releases as the only update channel** — simplest,
   matches the actual distribution surface (Releases already host the `.exe`
   and `.zip`), and removes the moving parts that caused the 100 MB problem.

**Decision.** Drop TUF entirely. Distribute via GitHub Releases (manual
download). Replace `AppUpdateController`'s TUF check with a one-call GitHub
Releases API check (`GET /repos/.../releases/latest`) that shows a banner if
the latest release tag is greater than the running version.

**Consequences.**
- Users must manually download updates. Mitigated by a clear in-app banner and
  a "View Releases" button that opens the latest release.
- The `gh-pages` branch is no longer needed and is deleted.
- The four `TUF_KEY_*` secrets are deleted.
- One new dependency: `httpx` (for the GitHub API call).
- ADR-0008 (Windows-only distribution) is unchanged.

## Files to Add

1. `src/skill_manager/core/release_check_service.py`
   - `check_latest_release() -> tuple[str | None, str | None]`
   - `httpx.get("https://api.github.com/repos/dishanagalawatta/SkillManager/releases/latest", timeout=10.0, headers={"Accept": "application/vnd.github+json", "User-Agent": "SkillManager"})`
   - Parse JSON, return `(version, None)` on success; `(None, error_msg)` on failure
   - 10-second timeout, no caching
2. `tests/test_release_check_service.py`
   - Mock `httpx.get` to return canned responses
   - Test success, 404 (no releases), 500 (server error), timeout, malformed JSON
3. `tests/test_ui_app_update_flow.py` (rewritten)
   - Mock `release_check_service.check_latest_release`
   - Test the UI flow: "Check for Updates" → banner shows "v1.6.0 available"

## Files to Delete

1. `scripts/publish_tuf_release.py`
2. `src/skill_manager/assets/tuf/root.json`
3. `src/skill_manager/assets/tuf/` (empty after root.json removed)
4. `tuf_keys/` (local, gitignored — clean up after secrets deleted)

## Files to Modify

### Production code

- `src/skill_manager/app.py`
  - KEEP `from skill_manager.controllers.app_update_controller import AppUpdateController`
  - KEEP `self.app_updater = AppUpdateController(self)`
  - REMOVE `QTimer.singleShot(500, self.app_updater.checkForUpdates)` (no startup auto-check)
  - REMOVE `self._update_check_timer` and its wiring (no periodic checks)
  - REMOVE `self.config_mgr.autoCheckUpdatesChanged.connect(self._update_periodic_check)` etc.
  - REMOVE the `autoCheckUpdatesChanged` / `autoDownloadUpdatesChanged` / `updateCheckIntervalHoursChanged` signal proxies
  - KEEP `app_update_controller` property (used by QML)

- `src/skill_manager/controllers/app_update_controller.py` (rewritten)
  - Replace TUF-backed `AppUpdateService` with `release_check_service`
  - Properties: `updateAvailable`, `latestVersion`, `isCheckingForUpdates`, `hasCheckedForUpdates`, `currentVersion`, `releaseUrl` (constant)
  - REMOVE: `isUpdating`, `updateProgress`, `downloadAndApplyUpdate`
  - Slot: `checkForUpdates(manual=False)` — calls `release_check_service`, emits signals
  - Slot: `openReleasesPage()` — calls `Qt.openUrlExternally("https://github.com/dishanagalawatta/SkillManager/releases/latest")`
  - Diagnostic categories: keep `CATEGORY_APP_UPDATE_*` (semantics unchanged for the UI)

- `src/skill_manager/core/update_service.py`
  - REMOVE the `AppUpdateService` class (lines ~578–735)
  - KEEP the `UpdateService` class (skill packages — unrelated)

- `src/skill_manager/core/diagnostics.py`
  - KEEP `CATEGORY_APP_UPDATE_*` constants (still used by `AppUpdateController`)
  - ADD `CATEGORY_RELEASE_CHECK = "release_check"`

- `src/skill_manager/core/schemas.py`
  - SIMPLIFY `AppUpdateState`: remove `is_updating`, `progress`; keep `is_checking`, `update_available`, `has_checked`, `current_version`, `latest_version`, `error`

- `src/skill_manager/controllers/config_controller.py`
  - REMOVE `autoCheckUpdates` property + signal + setter
  - REMOVE `autoDownloadUpdates` property + signal + setter
  - REMOVE `updateCheckIntervalHours` property + signal + setter

- `src/skill_manager/SkillManagerComponents/views/SettingsView.qml`
  - REMOVE the "Auto Check for Updates" and "Auto Download Updates" switches (lines 303–327)
  - In the "About" section, replace the dynamic update button with:
    - A "Check for Updates" button that calls `AppController.app_update_controller.checkForUpdates(true)`
    - A "View Releases" link button that calls `AppController.app_update_controller.openReleasesPage()`
    - A label that shows "v{latest} available" or "Up to date" based on `updateAvailable` / `hasCheckedForUpdates`
  - REMOVE the progress bar (lines 658–676)

- `pyproject.toml`
  - REMOVE `tufup>=0.10.0` from dependencies
  - ADD `httpx>=0.27` to dependencies
  - REMOVE `assets/tuf/*` from `skill_manager = [...]` package data

### CI

- `.github/workflows/release.yml`
  - REMOVE the `tuf-publish` job (lines 107–165)
  - REMOVE the `pages: write` permission (no longer needed)

### Docs

- `docs/RELEASING.md` — remove all TUF-related sections, secrets, troubleshooting
- `docs/CI_CD.md` — remove TUF publish from pipeline diagram, secrets table
- `docs/DEVELOPMENT.md` — remove TUF section
- `docs/ARCHITECTURE.md` — remove `AppUpdateController`/TUF sections
- `docs/API.md` — update or remove `app_update` row
- `docs/SECURITY.md` — remove GHSA-qp9x-wp8f-qgjj suppressed advisory
- `docs/VERSIONING.md` — remove TUF publish step from flow
- `ADR_INDEX.md` — ADD `ADR-0010: Drop TUF self-update, use GitHub Releases API`

## Manual Cleanup (post-merge)

After the new release is published:

1. Delete the `gh-pages` branch from remote:
   ```bash
   git push origin --delete gh-pages
   ```
2. Delete the four TUF signing key secrets:
   ```bash
   gh secret delete TUF_KEY_ROOT --repo dishanagalawatta/SkillManager
   gh secret delete TUF_KEY_SNAPSHOT --repo dishanagalawatta/SkillManager
   gh secret delete TUF_KEY_TARGETS --repo dishanagalawatta/SkillManager
   gh secret delete TUF_KEY_TIMESTAMP --repo dishanagalawatta/SkillManager
   ```
3. Local: remove `tuf_keys/` directory

## Version Bump

`[minor]` → v1.6.0 (user-facing feature loss: auto-update → manual)

## Verification

1. `uv run pytest tests/ -x` — all tests pass (existing app-update tests removed/rewritten)
2. `uv run ruff check .` — clean
3. `uv run ruff format --check .` — clean
4. CI passes: lint + test on Py 3.12 and 3.13 (5/5 green)
5. Release workflow runs successfully, creates v1.6.0 GitHub Release with `.exe` + `.zip` assets
6. Manual smoke test: launch app on Windows, click "Check for Updates" → see version comparison

## Risks

- **GitHub API rate limit**: 60 req/hour unauthenticated. Manual button is far
  below this. If users abuse, add a 24h local cache.
- **No delta updates**: Users always download the full ~137 MB installer. Same
  as before (TUF tar.gz was 320 MB, larger).
- **Migration**: Users on v1.5.4 (or earlier) must manually download v1.6.0.
  The v1.6.0 release notes will state this clearly.

## Rollback

If we need to revert: the v1.5.4 TUF keys are still in `tuf_keys/` (locally)
and the `gh-pages` branch is recoverable via GitHub UI. Re-add the
`TUF_KEY_*` secrets and restore the deleted files from git history.
