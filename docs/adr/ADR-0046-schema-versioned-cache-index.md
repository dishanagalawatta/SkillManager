# ADR-0046: Schema-Versioned Cache Index

> Status: **Accepted**
> Date: 2026-10-22
> Owner: @DIKKA

## Context

The discovery pipeline persists its prepared state to `cache.json`
(`SKILL_LIBRARY_CACHE_FILE`). The schema version constant
(`SKILL_LIBRARY_CACHE_VERSION` in `core/config.py`) existed but was never
enforced: an index written by an older build survived a record-layout change
and the model was populated from a stale shape — silently wrong filters,
sorting and counts until the next full rewrite.

## Decision

- `save_cache` stamps every written index with the current
  `SKILL_LIBRARY_CACHE_VERSION`.
- `load_cache` treats a **missing or mismatched** marker as untrustworthy: the
  stale file is discarded *and unlinked*, so the next startup performs a clean
  scan instead of serving an incompatible layout.

## Consequences

### Positive

- A cache written by an incompatible build can no longer poison the model;
  the failure mode degrades to "one extra scan", which is bounded and honest.
- The headless MCP loader inherits the same guarantee (see
  [MCP_SERVER.md](../MCP_SERVER.md)): it loads cache-only and therefore can
  never resurrect an old layout over a newer GUI's index.
- The unlink keeps the failure from repeating on every load.

### Negative

- A version bump costs users one full scan on first launch after upgrade.

### Neutral

- Only the marker matters today; per-field migrations stay out of scope —
  the cache is fully reproducible from the sources.
