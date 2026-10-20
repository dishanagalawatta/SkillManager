# ADR-0044: Automatic App-Release Checks with an Update Toast

> Status: **Accepted**
> Date: 2026-10-20
> Owner: @DIKKA

## Context

ADR-0010 replaced the TUF updater with a GitHub Releases version check, and
commit `63c121c` deliberately removed the periodic auto-check timer along with
TUF. Since then `AppUpdateController.checkForUpdates()` had exactly one caller:
the **Check for Updates** button in Settings.

The consequence was visible in practice: a user running v2.11.2 while v2.13.0
was published never learned about it. The app only told them when they opened
Settings and asked — and after a successful "up to date" result the button
disabled itself until restart, so the state could not even be refreshed.

Nothing was broken in the check itself: `GET /releases/latest` returns the
expected tag and `packaging.version` compares it correctly. The missing piece
was the automatic half of the feature.

## Decision

1. **Check automatically.** `AppUpdateController.startAutoCheck()` is armed by
   `AppController` after startup: one check ~4 s after launch, then daily while
   the app stays open (`AUTO_CHECK_INTERVAL_MS`). It is idempotent, so repeated
   calls cannot stack timers.
2. **Notify in-app.** A detected release emits `appUpdateAvailable(str)`, which
   `Main.qml` renders through the existing `UpdateToast` with a **View Release**
   action that opens the releases page. `UpdateToast` gains an `actionMode`
   (`packages` | `release`) so the package-update action is unchanged.
3. **Keep installation manual.** This ADR does **not** add silent installs.
   ADR-0010's "download from Releases" model stands: `.deb` needs root, the
   Windows installer is unsigned until SignPath is live, and silently replacing
   a user's installation is not a decision the app should make on its own.
4. **Never claim a check that did not happen.** Development builds (not
   `sys.frozen`) skip the automatic check without setting `has_checked`, so
   Settings cannot render "Up to Date" for a check that never contacted GitHub.
5. **Keep the Settings button usable.** It is disabled only while a check is in
   flight, not permanently after an up-to-date result.

## Consequences

### Positive

- Users learn about a release without opening Settings; the update path is one
  click away.
- One extra unauthenticated GitHub API request per launch per day — far below
  the 60/hour limit.
- No new dependencies, no privileged operations, no background downloads.

### Negative

- The toast is transient (10 s) and can be missed; the Settings state remains
  the durable indicator.
- Daily checks only run while the app is open; a user who never launches the
  app is never notified (acceptable for a desktop tool).

### Neutral

- Development builds still require a manual check (`manual=True`), which is what
  the verification harness uses.
- ADR-0010 remains the record for "no in-app install"; this ADR only restores
  the automatic *check*.

## Alternatives Considered

### Full self-update (download + install)

Rejected for now: platform-specific (silent `Setup.exe`, `pkexec dpkg -i`,
AppImage self-replace), requires privileged operations on Linux, and depends on
code signing that is not live yet (SignPath approval pending). Revisit once
signing lands.

### Check-only, no notification

Rejected: an invisible automatic check does not solve the reported problem —
the user still has to open Settings to discover the release.

### Restore the pre-TUF interval setting

Rejected: the removed `auto_check_updates` / `update_check_interval_hours`
settings added UI surface for no real benefit. A fixed daily cadence plus the
manual button covers both behaviours.

## References

- [ADR-0010](ADR-0010-drop-tuf.md) — drop TUF, check via GitHub Releases
- [`src/skill_manager/controllers/app_update_controller.py`](../../src/skill_manager/controllers/app_update_controller.py)
- [`src/skill_manager/SkillManagerComponents/UpdateToast.qml`](../../src/skill_manager/SkillManagerComponents/UpdateToast.qml)
