# ADR-0026: Workspace Standardization — 2026-08 Round

> Status: **Accepted**
> Date: 2026-08-16
> Owner: @DIKKA

## Context

The workspace standardization established by ADR-0022 and ADR-0023
needed a follow-up pass. The audit found:

- Regenerable build/test artifacts present on disk: `.pytest_cache/`,
  `.ruff_cache/`, `__pycache__/` trees, `build/`, `dist/`
  (incl. a ~393 MB portable zip), `src/skill_manager.egg-info`, stale
  MCP captures/ack receipts, the discovery disk cache, and leftover
  `test_xdg_data/`.
- `.gitignore` was missing several standard Python tool caches
  (`pip-wheel-metadata/`, `.pyre/`, `.dmypy.json`, `*.py,cover`,
  `cython_debug/`).
- Two conductor tracks (`command_skill_carry_20260623`,
  `multi_project_command_20260623`) were still `active` although their
  branches were deleted and the features shipped — violating the
  stale-track policy in `conductor/workflow.md`. Track 1 also carried
  a dangling `related_adrs` reference to non-existent ADR-0017.
- `docs/README.md` advertised ADRs only through `ADR-0023` (0024/0025
  existed) and omitted `SNAP_CAPTURE_VALIDATION.md` from the nav.
- `AGENTS.md` quick reference lacked the `pyright` type-check command.
- `DESIGN.md` documented token groups but not the concrete palette
  values behind them.
- `README.md` had no consolidated documentation navigation table.

## Decision

Standardize the workspace in one pass, following the ADR-0022/0023
precedent:

1. **Cleanup**: remove all regenerable artifacts listed above; keep
   `.venv/`, `.codegraph/` (index), tracked `data/*.json` runtime
   state, and the local `.env`.
2. **Gitignore**: add the missing standard Python tool caches under
   the Python section.
3. **Conductor**: mark both stale tracks `completed` (canonical
   metadata schema per `workflow.md`), correct the ADR-0017 → ADR-0020
   reference, and archive to `conductor/_archive/2026-08-16/`.
4. **Docs**: fix the `docs/README.md` ADR range and nav gaps; add the
   `pyright` row to `AGENTS.md`; add the semantic palette table to
   `DESIGN.md`; add the documentation navigation section to
   `README.md`; add a tier sanity-check to `environments/README.md`.
5. **ADR**: add this record and index it in `ADR_INDEX.md`.

## Consequences

### Positive

- Disk footprint reduced (~400 MB of build artifacts removed).
- `.gitignore` coverage matches current tooling output.
- Track lifecycle state reflects reality; dangling ADR reference fixed.
- Docs navigation is complete and self-consistent.

### Negative

- Documentation churn; new/edited entries need review.
- Archiving closes the historical record for two tracks (preserved in
  `_archive/`, never deleted).

### Neutral

- No runtime behavior changed; purely cleanup and documentation.

## Alternatives Considered

### Leave stale tracks active

Rejected — `workflow.md` mandates archival when a track's branch is
merged or deleted; stale `active` tracks degrade the lifecycle record.

### Rewrite AGENTS.md/DESIGN.md wholesale

Rejected — existing content is high-signal and enforced by the user;
targeted additive edits preserve the mandatory rules (UI validation,
input-injection safety).

## References

- `conductor/workflow.md` — stale-track policy and canonical metadata
- `docs/adr/ADR-0022-workspace-cleanup-standardization.md` — gitignore/archival precedent
- `docs/adr/ADR-0023-workspace-docs-environment-standardization.md` — docs/env precedent
- `docs/adr/ADR-0020-command-skill-pills.md` — decision record for the archived carry track
- `src/skill_manager/SkillManagerComponents/Theme.qml` — palette source of truth