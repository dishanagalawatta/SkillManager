# ADR-0023: Workspace Documentation & Environment Standardization

> Status: **Accepted**
> Date: 2026-08-04
> Owner: @DIKKA

## Context

The repository had accumulated documentation drift and configuration
gaps:

- `docs/API/index.md` listed 15 MCP tools; the server registers 29
  (several renamed/removed since the list was written).
- ADRs referenced by `docs/API.md` (ADR-0013, ADR-0014) did not exist
  on disk.
- `environments/README.md` contradicted `.env.prod.example` and
  `docs/ENVIRONMENT.md` on the production QML disk-cache setting.
- Tier example files were missing `SKILL_MANAGER_HOTKEY`.
- `.gitignore` did not cover `.env.*` variants or several common
  cache/dependency directories.
- `DESIGN.md` had an unclosed QML code fence and a stale MCP tool
  layout (`read_tools.py` → `skills.py`, `write_tools.py` → `write.py`,
  plus new `gui.py` / `monitor.py`).
- Completed conductor tracks (`mcp_server_20260720`,
  `fix_package_add_snap_to_latest`) were never marked completed or
  archived.

## Decision

Standardize the workspace in one pass:

1. **Documentation**: repair `DESIGN.md` (fence, MCP layout); refresh
   `docs/API/index.md` MCP inventory; create the missing ADR-0013 /
   ADR-0014; add ADR-0023; sync `docs/ENVIRONMENT.md` contract and
   `docs/README.md` hub.
2. **Environment**: align the three tier example files with the
   canonical `.env.example`; fix the tier-matrix contradiction; add
   `SKILL_MANAGER_HOTKEY` to all tiers.
3. **Gitignore**: add `.env.*` (re-including example files),
   `.hypothesis/`, `.tox/`, `.nox/`, `.eggs/`, `node_modules/`.
4. **Cleanup**: remove regenerable caches (`.coverage`,
   `.pytest_cache/`, `.ruff_cache/`, `__pycache__/`), stale lock files,
   and MCP capture screenshots.
5. **Conductor**: close and archive completed tracks with canonical
   metadata (per `conductor/workflow.md`).

## Consequences

### Positive

- API docs match the running MCP server; dangling ADR links resolve.
- The env contract is a single source of truth across all four
  templates.
- Gitignore hardening prevents accidental commits of local env files
  and dependency caches.
- Track lifecycle state reflects reality.

### Negative

- Documentation churn; the new ADR entries need review.
- `.env.*` ignore rules must keep the `!.env.example` exceptions in
  sync when new example files are added.

### Neutral

- No runtime behavior changed; purely documentation/configuration.

## Alternatives Considered

### Delete stale API docs instead of refreshing

Rejected — the MCP inventory is part of the agent-facing contract and
must stay accurate.

### Leave ADR gaps and track metadata as-is

Rejected — dangling references degrade the decision record's value as
a historical artifact.

## References

- `docs/API/index.md`, `docs/API.md`, `DESIGN.md`
- `environments/`, `.gitignore`, `docs/ENVIRONMENT.md`
- `conductor/workflow.md` (canonical metadata schema)
- ADR-0022 — previous workspace cleanup standardization
