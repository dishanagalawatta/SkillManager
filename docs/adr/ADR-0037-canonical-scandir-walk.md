# ADR-0037: Single Canonical Filesystem Walk

> Status: **Accepted**
> Date: 2026-09-20
> Owner: @DIKKA

## Context

Three different subsystems walked directory trees with three different
implementations: `skill_fingerprint` (own `os.scandir` loop),
`update_service._relative_file_map` (`os.walk` + `pathlib` per file),
and the MCP bridge `_walk` (`os.walk` with a skip list). Each copy had
slightly different symlink, sorting, and separator semantics, and every
performance or correctness fix had to be re-discovered per call site
(the 2026-09-11 Bolt log already recorded "do not inline a second copy
of the walk", yet PR #284 added exactly that).

## Decision

1. **One canonical walk**: `iter_relative_files()` in
   `core/skill_packages/storage.py` is the only directory-tree walk in
   `src/`. It is an iterative `os.scandir` traversal (~12x faster than
   the `os.walk` + `pathlib` pattern it replaces).
2. **Fixed semantics for all consumers**: symlinked files are listed
   (matching `Path.is_file()`), symlinked directories are never
   recursed into (matching `Path.rglob`), output is `/`-separated
   relative strings sorted by path parts (case-insensitive on
   Windows), and non-regular files (FIFOs, sockets, broken symlinks)
   are excluded.
3. **Consumers adapt, never reimplement**: `_relative_file_map`
   (PR #284), `skill_fingerprint`, and the MCP `static_analyze` walk
   (PR #287) are thin adapters over the helper — including the
   skip-list filter, which applies to directory parts only so a *file*
   sharing a junk name is still visited.
4. **No new walks**: any future feature needing a tree listing reuses
   the helper; a divergent need must amend this ADR first.

## Consequences

### Positive

- Walk performance work (PEP 471 `DirEntry` caching, string-slice
  relative paths) and symlink semantics live in one place.
- Deterministic sorted output everywhere; no filesystem-order
  dependence.
- Grep-style consumers can no longer block opening FIFOs.

### Negative

- Callers needing non-regular files must add an explicit opt-in to the
  helper (none exists today).
- `root / rel` reconstruction assumes `/`-separated input, which the
  helper guarantees but a future editor could break silently.

### Neutral

- `mcp/bridge/_static.py` keeps its own skip-list; only the traversal
  mechanism is shared.

## Alternatives Considered

### Per-call-site inline walks

What PR #284 originally did. Rejected: duplicates the hot loop,
drifts in symlink/sort semantics, and contradicts the recorded Bolt
learning.

### `pathlib.Path.rglob` everywhere

Simplest API, but reintroduces per-file `stat` round trips and
`Path` instantiation in hot loops — the exact cost the scandir work
removed.

## References

- PR #279 (skill discovery walk), PR #284, PR #287
- PEP 471 (`os.scandir` rationale)
- `.jules/bolt.md` 2026-09-11 learning ("do not inline a second copy")
