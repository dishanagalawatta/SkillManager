# ADR-0013: Package Add Snap-to-Latest Policy

> Status: **Accepted**
> Date: 2026-06-22
> Owner: @DIKKA

## Context

Newly added skill packages (git / npx / custom sources) showed
"Outdated" immediately after registration because `current_version`
could not be detected at add time:

- git sources whose local clone path was entered as the install path
  (not the clone path) have no detectable local version;
- non-git sources without a `current_version_command` have no local
  version mechanism at all.

Showing "Outdated" on a fresh add is misleading — the user just
registered the latest version.

## Decision

`addSkillPackage` performs a two-phase version check:

1. **Detect** — resolve `latest_version` (remote tag,
   `latest_version_command`, npm registry).
2. **Snap** — if `latest_version` is available and `current_version` is
   empty (and no `current_version_command` overrides detection), snap
   `current_version = latest_version`.

If `latest_version` cannot be detected at all, the add is **blocked**
with an inline error; the dialog stays open and nothing is appended.

The snap is implemented in `_sync_current_to_latest_if_applicable()`
(`core/skill_packages/versioning.py`) and is shared with the
post-update sync path (`force_refresh`).

## Consequences

### Positive

- Freshly added packages show "Up to Date" until the registry moves.
- An undetectable latest version is surfaced inline instead of
  silently registering a broken package.
- The QML dialog contract changed to `@Slot(dict, result=str)` returning
  `{"ok", "error", "name"}`; callers inspect the return value.

### Negative

- `current_version` is not independently verified at add time; it is
  corrected on the first successful update.
- Sources that set `current_version_command` keep explicit control and
  are never snapped.

### Neutral

- Adds an extra version-detection pass on add (remote tag fetch).

## Alternatives Considered

### Register without version info

Rejected — leaves the package permanently marked "Outdated".

### Snap unconditionally

Rejected — would override a user's explicit `current_version_command`.

### Block add on any detection failure

Rejected — `latest_version` may legitimately be empty for custom
sources that pin versions manually.

## References

- `src/skill_manager/core/skill_packages/versioning.py`
- `src/skill_manager/controllers/update_controller.py` (`addSkillPackage`)
- `src/skill_manager/SkillManagerComponents/dialogs/PackageEditDialog.qml`
- [`docs/API.md` § 4](../API.md) — package add/edit return contract
