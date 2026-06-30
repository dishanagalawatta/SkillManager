# ADR-0018: Workspace Standardization

> Status: **Accepted**
> Date: 2026-05-25
> Owner: @DIKKA

## Context

The SkillManager workspace had accumulated organizational debt:

- Root-level scripts (`run.py`, `run_tests.py`, `Launch_SkillManager.vbs`) with no clear home
- Misplaced documentation (`src/posthog-setup-report.md`)
- Incomplete `.gitignore` (`.env` not excluded, runtime state not gitignored)
- Incomplete documentation (`README.md` 15 lines, `AGENTS.md` 7 lines, `DESIGN.md` 7 lines)
- Missing ADR files (index referenced ADRs that didn't exist as files)

## Decision

Standardize the workspace according to these rules:

### File Organization

| File | Before | After |
|------|--------|-------|
| `Launch_SkillManager.vbs` | Root | `packaging/windows/` |
| `run.py` | Root | `scripts/dev_run.py` |
| `run_tests.py` | Root | `scripts/dev_test.py` |
| `src/posthog-setup-report.md` | `src/` | `docs/PRODUCT_TELEMETRY.md` |

### Gitignore Rules

- Add `.env` (secrets)
- Add `data/` (runtime state)
- Add `*.bak`, `*.tmp`, `*~`, `*.orig`, `Thumbs.db`, `Desktop.ini`
- Organize into sections: IDE, OS, Python, Qt, Runtime, Agent, Secrets

### Documentation Standards

- `README.md`: Full project overview (300+ lines)
- `AGENTS.md`: Agent constraints, conventions, workflow
- `DESIGN.md`: Design patterns, architecture, data flow
- `docs/adr/`: All ADRs as individual files
- `ADR_INDEX.md`: Rebuilt with status, dates, cross-references

### Conductor Lifecycle

- Completed tracks archived immediately to `conductor/_archive/<date>/`
- Active tracks remain in `conductor/tracks/`

## Consequences

### Positive

- Clear separation of concerns (dev scripts, packaging, docs)
- Security posture improved (`.env` excluded, secrets not committed)
- Documentation completeness (all referenced files exist)
- Agent workflow clarity (AGENTS.md provides full context)

### Negative

- One-time effort to move files and rewrite docs
- Contributors must update bookmarks/references

### Neutral

- `pyproject.toml` entry point (`skill-manager`) unchanged
- CI/CD workflows unaffected (use `uv run` commands)

## Alternatives Considered

### Minimal cleanup (just `.gitignore`)

Rejected — half-measure; root scripts and stub docs remain.

### Full restructure with `src/` → `lib/` rename

Rejected — too disruptive; current `src/skill_manager/` convention is standard.

## References

- [`docs/HOUSEKEEPING.md`](../HOUSEKEEPING.md) — cleanup rules
- [`conductor/workflow.md`](../../conductor/workflow.md) — archival lifecycle
- ADR-0016 — `.opencode` gitignore policy
