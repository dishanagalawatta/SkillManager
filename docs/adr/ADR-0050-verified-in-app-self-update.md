# ADR-0050: Verified, Consent-Gated In-App Self-Update

> Status: **Accepted**
> Date: 2026-10-29
> Owner: @DIKKA

## Context

ADR-0044 restored the automatic release *check* and the update toast, but kept
installation manual. Two problems remained in shipped builds:

1. **"View Release" could do nothing.** `QDesktopServices.openUrl()` delegates
   to `xdg-open` on Linux, which delegates to `gio open` on GNOME. A packaged
   PyInstaller/AppImage process exports its bundled `LD_LIBRARY_PATH`; the host
   `gio` binary then loads the bundled `libgio` and dies with
   `undefined symbol: g_unix_mount_entry_get_options`. The launcher process was
   spawned successfully, so Qt reported success and no error reached the user.
   The toast had a second, independent defect: `UpdateToast.qml` referenced the
   `AppController` singleton without `import App 1.0`. Its signal handlers
   therefore threw `ReferenceError` on click, which visual validation confirmed
   as a no-op even outside a packaged build.
2. **There was no install path.** Even when the user found the release page,
   an AppImage user had to replace the file by hand, and `.deb` / Windows users
   had to re-run an installer. The toast promised an update the app could not
   deliver.

The release pipeline already publishes `SHA256SUMS` next to every artifact, so
the missing piece was an in-app consumer for it — not a new trust model.

## Decision

1. **Explicit consent only.** The automatic check still only *announces* a
   release. Bytes are downloaded and installed only after the user clicks
   **Update Now** (toast) or **Download & Install** (Settings / Updates hub).
   There is no background download and no silent install.
2. **Verify before executing.** Every download must:
   - resolve from an allow-listed HTTPS GitHub host (`github.com`,
     `objects.githubusercontent.com`, `release-assets.githubusercontent.com`),
     including after redirects;
   - match the release `SHA256SUMS` entry for that exact asset;
   - be written to a `.part` file and moved into place only after the digest
     matches;
   - refuse the install when the manifest is missing or has no entry. The shell
     installer only warns in that case; an in-app installer must not execute
     unverified bytes.
3. **One installer per install kind** (`core/app_update_service.py`):

   | Detected build | Mechanism | Relaunch |
   |----------------|-----------|----------|
   | AppImage (`APPIMAGE` env) | `os.replace` next to the target, atomic on the same filesystem | Immediately via `QProcess.startDetached` |
   | `.deb` (frozen, no `APPIMAGE`) | Detached `/bin/sh` helper waits for the app PID, then `pkexec` + `apt-get install -y --allow-downgrades` (or `dpkg -i`) | Helper starts the installed binary |
   | Windows installer (frozen `.exe`) | Detached `.cmd` waits for the PID, then Inno Setup `/SILENT /SUPPRESSMSGBOXES /NORESTART /CLOSEAPPLICATIONS` | Helper starts the installed `.exe` |
   | Source checkout | Not self-updatable; points at `scripts/update-local.sh` / the release page | — |

   A source checkout is excluded on purpose: replacing a working tree is a
   developer action, not a release-artifact action.
4. **Repair the opener environment, don't trust the spawn.** `View Release`
   now goes through `utils/external_url.py`, which launches `gio`/`xdg-open`/
   `kde-open5`/`sensible-browser` with `utils.linux.get_clean_env()` (the same
   `LD_LIBRARY_PATH` repair used for clipboard and input helpers). Only a zero
   exit code counts as success; `QDesktopServices` remains a last-resort
   fallback, and a real failure is reported in the status bar and diagnostics
   instead of silently doing nothing. Every QML file that touches the
   `AppController` singleton imports `App 1.0`; the QML contract test now
   asserts this for the update surfaces.
5. **One shared surface.** `AppUpdateCard.qml` renders the whole lifecycle
   (check, progress, cancel, failure, platform reason) and is mounted in both
   Settings → About and the Updates hub. The toast offers **View Release**
   (always) plus **Update Now** (only when this build can install itself).

## Consequences

### Positive

- The two reported defects are fixed at the root: the release page opens even
  in a poisoned packaged environment, and the update can be installed from the
  app.
- Users get checksum-verified bytes; a compromised API response cannot redirect
  the download to another host.
- Failure modes are visible: download errors, checksum mismatches, missing
  `pkexec`, and read-only AppImage locations all surface in the UI.

### Negative

- The `.deb` path needs `pkexec` and polkit authorization; without them the
  card explains why and falls back to the release page.
- The Windows installer is still unsigned until SignPath is live. The in-app
  path inherits that risk; it does not add or remove it.
- AppImage replacement requires a writable directory; installed-by-root
  AppImages report that limit instead of pretending to update.

### Neutral

- ADR-0010's TUF removal stands; this ADR adds checksum verification on top of
  GitHub Releases, not a new signing infrastructure.
- ADR-0044's automatic check and toast behaviour stands. Its "installation
  stays manual" clause is superseded by the consent-gated installer above.
- Helper scripts log to `<app data>/update-install.log` so a failed privileged
  step can be diagnosed after the app exits.

## Alternatives Considered

### Keep installation manual

Rejected: it was the reported bug. A desktop app that can detect, download and
verify an update should be able to hand it to the platform installer.

### Background download as soon as a release is detected

Rejected: bandwidth and disk writes without consent, and it makes "no update"
hard to reason about on metered connections. The checksum and consent model
stays one click.

### Use `QDesktopServices` only and document the `LD_LIBRARY_PATH` workaround

Rejected: it pushes a packaging bug onto users and still leaves the button
silently broken on the most common Linux desktop.

### Shell out to the existing `install.sh --update`

Rejected for the in-app path: it re-downloads a script over the network and
loses the asset/checksum binding the app already has. The installer script
remains the terminal workflow.

## References

- [ADR-0010](ADR-0010-drop-tuf.md) — drop TUF, check via GitHub Releases
- [ADR-0044](ADR-0044-automatic-app-release-checks.md) — automatic checks + toast
- [`core/app_update_service.py`](../../src/skill_manager/core/app_update_service.py)
- [`core/release_check_service.py`](../../src/skill_manager/core/release_check_service.py)
- [`utils/external_url.py`](../../src/skill_manager/utils/external_url.py)
- [`AppUpdateCard.qml`](../../src/skill_manager/SkillManagerComponents/AppUpdateCard.qml)
