# ADR-0014: Package Edit Snap-to-Latest Policy

> Status: **Accepted**
> Date: 2026-06-22
> Owner: @DIKKA

## Context

Editing an existing skill package could leave `current_version` stale
or empty after the user changed source details (repository URL, source
type, version commands). The edit path must behave like the add path
(ADR-0013): resolve `latest_version` first and refuse to persist an
edit that cannot resolve it.

## Decision

`updateUpdatePackage` follows the same two-phase contract as
`addSkillPackage` (ADR-0013): normalize → validate → detect
`latest_version` → snap `current_version` to it when applicable →
commit. On failure it returns `{"ok": false, "error": ...}` and does
not overwrite the existing record. Internal state (`is_updating`,
`just_finished`, `last_updated`) is preserved across edits.

## Consequences

### Positive

- An edit never silently persists a broken or stale version pair.
- QML can show an inline `saveError` and keep the dialog open.

### Negative

- The edit path performs a remote version fetch when the repository
  URL changes.

### Neutral

- Return contract matches `addSkillPackage` (`result=str`, JSON).

## Alternatives Considered

### Persist edit without version check

Rejected — reintroduces the misleading "Outdated" state addressed by
ADR-0013.

## References

- `src/skill_manager/controllers/update_controller.py`
  (`updateUpdatePackage`)
- `src/skill_manager/SkillManagerComponents/dialogs/PackageEditDialog.qml`
- ADR-0013 — same snap policy on the add path
