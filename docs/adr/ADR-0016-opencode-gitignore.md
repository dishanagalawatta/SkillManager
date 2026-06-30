# ADR-0016: `.opencode` Gitignore Policy

> Status: **Accepted**
> Date: 2026-05-22
> Owner: @DIKKA

## Context

The `.opencode/` directory contains local agent tooling configuration (MCP servers, LSP settings, session data). This is machine-specific and should never be committed to the repository.

## Decision

Add `.opencode/` to `.gitignore` with the following rules:

```gitignore
# Agent / Local Tooling
# Per ADR-0016: .opencode/ is local agent config, never committed.
.opencode/
```

This applies to:
- `opencode.jsonc` (project-level config — committed as reference)
- `.opencode/` directory (runtime state — gitignored)

## Consequences

### Positive

- Prevents accidental commit of local agent configuration
- Each developer/opencode instance maintains its own settings
- Reference config (`opencode.jsonc`) provides sensible defaults

### Negative

- New contributors must create `.opencode/` locally (one-time setup)

### Neutral

- `opencode.jsonc` at project root is committed as a reference template
- `.opencode/` contents are fully regenerable

## Alternatives Considered

### Commit `.opencode/`

Rejected — contains machine-specific paths and session state.

### Use a `.opencode.example/`

Rejected — overkill; `opencode.jsonc` serves as the reference.

## References

- [`opencode.jsonc`](../../opencode.jsonc) — committed reference config
- [`docs/HOUSEKEEPING.md`](../HOUSEKEEPING.md) — cleanup rules
