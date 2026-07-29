# ADR-0022: Workspace Cleanup & Gitignore Standardization

## Status

Accepted — 2026-07-29

## Context

During a comprehensive workspace audit (SkillManager v1.8.0), four previously-unignored
local-tooling directories were discovered in the repository root:

- `.jules/` — Jules AI agent context files (3 markdown files, ~28 KB)
- `.codegraph/` — IDE code graph index (~19 MB)
- `.icons_temp/` — Temporary icon staging directory (empty)
- `.playwright-mcp/` — Playwright MCP adapter logs (~16 KB)

Additionally, a 53 MB diagnostic log (`shutdown_diag.log`) was present and
three conductor tracks with `done`/`completed`/`complete` status had not been
archived per [ADR-0015](ADR-0015-conductor-archival.md):

- `command_emoji_customization_20260721` (status: `done`)
- `freeze_popup_fix_20260701` (status: `completed`)
- `mcp_screenshot` (status: `complete`)

The existing `.gitignore` covered `.opencode/` and `.omo/` (per ADR-0016) but
lacked rules for the four new local-tooling directories. The `*.log` wildcard
covered `shutdown_diag.log` implicitly, but explicit documentation of intent
was absent.

## Decision

1. **Gitignore hardening**: Add explicit rules to `.gitignore` for `.jules/`,
   `.codegraph/`, `.icons_temp/`, and `.playwright-mcp/` under the Agent/Local
   Tooling section. Add explicit `shutdown_diag.log` rule under a new
   "Build / Runtime Diagnostic Artifacts" section (belt-and-suspenders alongside
   the `*.log` wildcard).

2. **Bulk cache cleanup**: Remove all regenerable artifacts (listed in
   `docs/HOUSEKEEPING.md`) in a single pre-standardization sweep:
   - `dist/` (804 MB), `build/` (56 MB), `shutdown_diag.log` (53 MB)
   - `.codegraph/` (19 MB), `.omo/`, `.jules/`, `.playwright-mcp/`
   - `.ruff_cache/`, `.pytest_cache/`, `.coverage`, `src/*.egg-info/`
   - All `__pycache__/` trees and `.pyc` files

3. **Conductor track archival**: Move three completed tracks to
   `conductor/_archive/2026-07-29/` per ADR-0015 archival policy.

4. **Documentation standardization**: Comprehensive updates to README.md,
   DESIGN.md, ADR_INDEX.md, docs/API/index.md, docs/README.md,
   environments/README.md, .env.example, and conductor/workflow.md.

## Consequences

### Positive

- Repository size reduced by ~930 MB of regenerable artifacts
- All local-tooling directories are now explicitly ignored, preventing
  accidental future commits of agent config files
- Three completed conductor tracks archived, keeping `conductor/tracks/`
  focused on active work (4 active tracks remain)
- Documentation is enriched with Tech Stack, Prerequisites, Troubleshooting,
  MCP architecture, and Error Handling sections
- Conductor metadata schema inconsistencies are documented in workflow.md

### Negative

- Developers who relied on `.codegraph/` or `.omo/` for local navigation
  will need to regenerate those indexes (they are regenerable on first use)

### Neutral

- The `*.log` wildcard already covered `shutdown_diag.log`; the explicit
  rule is redundant but documents intent for maintainers

## Related

- [ADR-0010](ADR-0010-drop-tuf.md) — Drop TUF (prior large-artifact removal)
- [ADR-0015](ADR-0015-conductor-archival.md) — Conductor archival policy
- [ADR-0016](ADR-0016-opencode-gitignore.md) — `.opencode` gitignore policy
- [ADR-0018](ADR-0018-workspace-standardization.md) — Workspace standardization
- [`docs/HOUSEKEEPING.md`](../HOUSEKEEPING.md) — Cleanup targets and rules
