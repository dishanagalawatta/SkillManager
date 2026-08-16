# Architecture Decision Records

> ADRs capture the context and rationale behind significant technical decisions.
> Each ADR is a standalone file in `docs/adr/`.

## Index

| ADR | Title | Status | Date | Owner |
|-----|-------|--------|------|-------|
| [ADR-0010](docs/adr/ADR-0010-drop-tuf.md) | Drop TUF (The Update Framework) | Accepted | 2026-05-15 | @DIKKA |
| [ADR-0013](docs/adr/ADR-0013-package-add-snap-to-latest.md) | Package Add Snap-to-Latest Policy | Accepted | 2026-06-22 | @DIKKA |
| [ADR-0014](docs/adr/ADR-0014-package-edit-snap-to-latest.md) | Package Edit Snap-to-Latest Policy | Accepted | 2026-06-22 | @DIKKA |
| [ADR-0015](docs/adr/ADR-0015-conductor-archival.md) | Conductor Root Plan Archival | Accepted | 2026-05-20 | @DIKKA |
| [ADR-0016](docs/adr/ADR-0016-opencode-gitignore.md) | `.opencode` Gitignore Policy | Accepted | 2026-05-22 | @DIKKA |
| [ADR-0018](docs/adr/ADR-0018-workspace-standardization.md) | Workspace Standardization | Accepted | 2026-05-25 | @DIKKA |
| [ADR-0019](docs/adr/ADR-0019-multiprocessing-joblib.md) | Multiprocessing with Joblib | Accepted | 2026-05-28 | @DIKKA |
| [ADR-0020](docs/adr/ADR-0020-command-skill-pills.md) | Command Inspector Skill-Dependency Pills | Accepted | 2026-06-14 | @DIKKA |
| [ADR-0021](docs/adr/ADR-0021-frozen-joblib-threads.md) | Frozen-build joblib backend override | Accepted | 2026-07-01 | @DIKKA |
| [ADR-0022](docs/adr/ADR-0022-workspace-cleanup-standardization.md) | Workspace Cleanup & Gitignore Standardization | Accepted | 2026-07-29 | @DIKKA |
| [ADR-0023](docs/adr/ADR-0023-workspace-docs-environment-standardization.md) | Workspace Documentation & Environment Standardization | Accepted | 2026-08-04 | @DIKKA |
| [ADR-0024](docs/adr/ADR-0024-dual-write-clipboard-verification.md) | Verified Dual-Write Clipboard Handling | Accepted | 2026-08-12 | @DIKKA |
| [ADR-0025](docs/adr/ADR-0025-selection-persistence-shutdown-sync.md) | Selection State Synchronization and Shutdown Persistence | Accepted | 2026-08-13 | @DIKKA |
| [ADR-0026](docs/adr/ADR-0026-workspace-2026-08-standardization.md) | Workspace Standardization — 2026-08 Round | Accepted | 2026-08-16 | @DIKKA |
| [ADR-0027](docs/adr/ADR-0027-path-self-healing-and-two-phase-incubation.md) | Storage Path Self-Healing Normalization & Two-Phase Model Incubation | Accepted | 2026-08-17 | @DIKKA |

## Template

See [`docs/adr/0000-template.md`](docs/adr/0000-template.md) for the ADR format.

## Status Key

- **Proposed** — Under discussion; not yet decided
- **Accepted** — Decision made and implemented
- **Superseded** — Replaced by a newer ADR
- **Deprecated** — No longer relevant

## Process

**When to write an ADR:**
- A significant architectural change is being made (new subsystem, pattern change, dependency swap)
- A decision affects multiple files or teams and its rationale should be preserved
- You are choosing between two or more non-trivial technical alternatives

**When NOT to write an ADR:**
- Routine bug fixes or minor patches
- Internal refactoring with no external interface change
- Adding a single utility function

**How to create one:**

```bash
# 1. Copy the template
cp docs/adr/0000-template.md docs/adr/ADR-XXXX-short-title.md

# 2. Fill in all sections (Context, Decision, Consequences)
# 3. Set status to "Proposed" until reviewed
# 4. Add entry to this index table
# 5. Reference in related DESIGN.md or ARCHITECTURE.md if applicable
```

**Key rules** (from `/architecture-decision-records` skill):
- Keep ADRs to 1–2 pages max
- Never modify an accepted ADR — supersede it with a new one
- Be honest about cons and trade-offs

## Navigation

| Related Document | Purpose |
|-----------------|----------|
| [`DESIGN.md`](DESIGN.md) | System design and architectural patterns |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | Full architecture with diagrams |
| [`docs/adr/0000-template.md`](docs/adr/0000-template.md) | ADR authoring template |
| [`conductor/workflow.md`](conductor/workflow.md) | Feature track lifecycle |
| [`docs/CONTRIBUTING.md`](docs/CONTRIBUTING.md) | Contribution guidelines |
