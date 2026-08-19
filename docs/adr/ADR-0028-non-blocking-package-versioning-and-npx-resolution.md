# ADR-0028: Non-Blocking Package Versioning and NPX / GitHub Shorthand Resolution

> Status: **Accepted**
> Date: 2026-08-19
> Owner: @DIKKA

## Context

When adding skill packages (e.g. `vercel-labs/find-skills` or community npx packages), synchronous version detection executed on the Qt Main Event Loop in `UpdateController.addSkillPackage` and `updateUpdatePackage`. This invoked long-running `subprocess.run` (with 30s timeouts and retry loops) and remote network `git ls-remote` commands.

Furthermore:
- `config.py` generated `latest_version_command` as `npx npm show -- {pkg} version`, which incorrectly attempted to execute `npm` through `npx`.
- Packages specified as `owner/repo` (e.g. `vercel-labs/find-skills`) caused `npm view` to attempt SSH Git connections (`ssh://git@github.com/...`), resulting in exit code 128 failures and hangs.
- When `latest_version` could not be resolved, the application hard-blocked package creation with an error message, preventing legitimate offline, custom, or sub-skill package registrations while triggering OS-level `"SkillManager" Is Not Responding` freeze modals.

## Decision

1. **Direct HTTP NPM Registry Probing (`fetch_npm_registry_version`)**:
   - Query `https://registry.npmjs.org/{pkg}/latest` via standard HTTP request with a strict 3.0s timeout.
   - Eliminates subprocess and shell overhead, resolving standard and scoped (`@scope/pkg`) npm versions in <100ms.

2. **Automatic GitHub Shorthand Resolution**:
   - When a package name follows the `owner/repo` format without `@` (e.g. `vercel-labs/find-skills`), probe the remote repository at `https://github.com/{owner}/{repo}.git` via `get_git_tag(..., is_remote=True)` with HTTPS protocol safety.

3. **Fast Command Timeouts and Removal of Blocking Retry Loops**:
   - Cap `run_version_command` execution at 5.0s and eliminate blocking retry loops during version probing to prevent UI thread lockups.

4. **Graceful Fallback & Snap-to-Latest**:
   - For valid package configurations where remote tags cannot be detected (e.g. offline, private repository, or sub-skill directory), default `latest_version` to `"latest"` and snap `current_version` accordingly.
   - Allow the package to be added immediately with "Up to Date" status while background installation and relocation execute on `BackgroundTaskRunner`.

## Consequences

### Positive

- Zero UI freezes or OS "Not Responding" modals during package creation and editing.
- Sub-100ms version resolution for NPM packages via direct HTTP registry queries.
- First-class support for `owner/repo` package shorthands (e.g. Vercel Labs AI skills).
- Users are never trapped in error dialogs when adding local, offline, or private skill packages.

### Negative

- Packages without public registry or git tags will display `"latest"` until an update run installs and detects local version files.

### Neutral

- Preserves the `{"ok": bool, "error": str | None, "name": str}` JSON return contract established in ADR-0013 and ADR-0014.

## Alternatives Considered

### Full async QML dialog refactoring with WebSockets / signal queues

Rejected — Unnecessary complexity. Using fast HTTP lookups (3.0s timeout), immediate in-memory normalization, and delegating downloads to `BackgroundTaskRunner` achieves instant UI responsiveness without altering the QML dialog contract.

### Block package registration on all detection failures

Rejected — Prevents offline usage and breaks compatibility with sub-skill directories and private repositories.

## References

- `src/skill_manager/core/skill_packages/versioning.py`
- `src/skill_manager/core/skill_packages/config.py`
- `src/skill_manager/controllers/update_controller.py`
- [`ADR-0013: Package Add Snap-to-Latest Policy`](ADR-0013-package-add-snap-to-latest.md)
- [`ADR-0014: Package Edit Snap-to-Latest Policy`](ADR-0014-package-edit-snap-to-latest.md)
