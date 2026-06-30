# ADR-0015: Conductor Root Plan Archival

> Status: **Accepted**
> Date: 2026-05-20
> Owner: @DIKKA

## Context

Conductor tracks accumulate in `conductor/tracks/` as features are implemented. Without a lifecycle policy, the directory grows indefinitely, making it hard to identify active vs. completed work.

## Decision

Implement a two-stage archival process:

1. **Immediate archival**: When a track's status becomes `completed` or `complete`, move it to `conductor/_archive/<date>/`
2. **Periodic review**: Monthly review of `conductor/tracks/` for stale active tracks (no updates in 30+ days)

Archive structure:
```
conductor/_archive/
├── 2026-05-20/
│   ├── track-name-1/
│   └── track-name-2/
├── 2026-06-30/
│   └── ...
└── tracks.md  (master archive index)
```

## Consequences

### Positive

- `conductor/tracks/` stays clean (only active/in-progress work)
- Historical context preserved in `_archive/`
- Date-based archive folders enable easy timeline navigation

### Negative

- Requires discipline to archive promptly after completion
- Archive search requires traversing date folders

### Neutral

- `conductor/workflow.md` documents the archival lifecycle
- `docs/HOUSEKEEPING.md` includes archival rules

## Alternatives Considered

### Delete completed tracks

Rejected — loses valuable context about what was done and why.

### Keep all tracks in `tracks/`

Rejected — directory becomes unwieldy; active tracks lost in noise.

## References

- [`conductor/workflow.md`](../../conductor/workflow.md) — lifecycle documentation
- [`docs/HOUSEKEEPING.md`](../HOUSEKEEPING.md) — cleanup rules
