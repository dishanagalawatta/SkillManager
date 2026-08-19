# Product Definition

> North-star for SkillManager. Updated only when the product scope
> changes. All scope changes require a track under
> [`conductor/tracks/`](tracks/).

## Identity

- **Name.** SkillManager.
- **Category.** Desktop productivity / developer utility.
- **Platforms.** Windows only (see [`../ADR_INDEX.md`](../ADR_INDEX.md)).
- **Stack.** Python 3.12+, PySide6 (Qt 6.8+), QML, `uv`, `ruff`.

## Goals

- Browse, copy, and organise AI agent skills across project repositories.
- Synchronise skills across repos with surgical, non-destructive updates.
- Capture screenshots with PII redaction for AI context.
- Notify users of new releases via the GitHub Releases API (see ADR-0010).
- Schedule background work via `apscheduler`.
- Persist configuration via `pydantic-settings`.

## Non-Goals

- macOS / Linux desktop builds.
- TUF-based secure auto-update (replaced by ADR-0010).
- Per-skill cloud sync.

## Cross-references

- Workflow: [`conductor/workflow.md`](workflow.md)
- Tech stack: [`conductor/tech-stack.md`](tech-stack.md)
- ADRs: [`../ADR_INDEX.md`](../ADR_INDEX.md)
- API: [`../docs/API.md`](../docs/API.md)
- Design: [`../DESIGN.md`](../DESIGN.md)
