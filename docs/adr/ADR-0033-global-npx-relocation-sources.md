# ADR-0033: Global npx Skill Installs as Relocation Sources

> Status: **Proposed**
> Date: 2026-09-08
> Owner: @DIKKA

## Context

`npx skills add <repo> -g/--global` installs into the user's global store
(`~/.agents/skills` plus per-agent symlinks), bypassing the staging temp dir
that `run_skill_package_update` uses as its working directory. The relocation
security gate in `relocate_packages_from_output` rejected every path outside
staging, so the only valid install path (e.g. `~/.agents/skills/archify`) was
discarded with `Ignored path outside of staging directory`, leaving the
isolated package storage empty while the CLI reported success — a silent
partial install. The stored `verify_command` also carried unbalanced quoting
(`echo "Skills installed in "{path}`).

## Decision

- Treat a fixed allowlist of well-known global skills stores
  (`~/.agents/skills`, `~/.claude|codex|cursor|gemini|opencode` skills,
  XDG data `skills`) as safe relocation **copy** sources via
  `known_global_skill_dirs()` / `is_allowed_global_source()`.
- The global install is preserved (copy, never move); contents are mirrored
  into isolated package storage so discovery, inventory, and sync keep working.
- Truly arbitrary outside-staging paths are still rejected.
- Regenerate `verify_command` with balanced quoting:
  `test -d <path> && echo "Skills installed in <path>"`.

## Consequences

### Positive

- `-g/--global` package installs complete instead of silently yielding zero skills.
- No change to the staging isolation model for project-local installs.
- Security posture preserved: narrow store allowlist, copy semantics, existing
  rejection test still green.

### Negative

- Global installs are duplicated on disk (global store + isolated package copy).
- Per-agent partial failures (e.g. PromptScript rejecting global installs) still
  surface as top-level failure lines from the upstream CLI.

### Neutral

- Packages installed before this fix have an empty storage dir and a malformed
  `verify_command`; both self-heal on the next update run.

## Alternatives Considered

### Strip `-g` and force local installs into staging

Would change user intent (global availability across projects) and break the
documented `npx skills add <repo> -g` workflow. Rejected.

### Point package storage directly at the global store (no copy)

Would couple isolated inventory/sync to a directory the external CLI mutates
outside our control. Rejected in favor of mirror-into-storage.

## References

- vercel-labs/skills README (global `-g` scope, `~/.agents/skills` canonical store)
- App log `skill_manager.log` 2026-09-08 (`Ignored path outside of staging directory`)
