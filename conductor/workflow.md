# Conductor Workflow

> Conductor manages the lifecycle of feature tracks in SkillManager.
> All active tracks live in `conductor/tracks/`.
> Completed tracks are archived to `conductor/_archive/<date>/`.

## Track Lifecycle

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   Proposed   │───▶│   Active     │───▶│  Completed   │───▶│  Archived    │
│  (create     │    │  (working)   │    │  (merged)    │    │  (preserved) │
│  metadata)   │    │              │    │              │    │              │
└──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘
```

### 1. Create a Track

```bash
mkdir -p conductor/tracks/<track-name>
```

Create `metadata.json`:

```json
{
  "slug": "<track-name>",
  "title": "Human-readable title",
  "status": "active",
  "owner": "@username",
  "created": "YYYY-MM-DD",
  "description": "Brief description of the track"
}
```

Create `plan.md` (required) and optionally `spec.md`.

### 2. Work the Track

- Edit `plan.md` with tasks, subtasks, and checkboxes
- Reference ADRs if making architectural decisions
- Update `metadata.json` status as you progress

### 3. Complete the Track

When all tasks are done and the branch is merged:

1. Update `metadata.json`:
   ```json
   {
     "status": "completed",
     "completed": "YYYY-MM-DD"
   }
   ```

2. Archive immediately:
   ```bash
   mkdir -p conductor/_archive/YYYY-MM-DD
   mv conductor/tracks/<track-name> conductor/_archive/YYYY-MM-DD/
   ```

### 4. Archive Rules (ADR-0015)

- **Immediate archival**: Completed tracks move to `_archive/<date>/` immediately
- **Periodic review**: Monthly check for stale active tracks (no updates in 30+ days)
- **Never delete**: Archived tracks are preserved for historical context

## File Templates

### metadata.json

```json
{
  "slug": "feature-name",
  "title": "Feature Name",
  "status": "active|completed",
  "owner": "@username",
  "created": "YYYY-MM-DD",
  "completed": "YYYY-MM-DD",
  "description": "What this track implements",
  "related_adrs": ["ADR-00XX"]
}
```

### plan.md

```markdown
# Plan: Feature Name

## Tasks

- [ ] Task 1
- [ ] Task 2
  - [ ] Subtask 2a
  - [ ] Subtask 2b
- [ ] Task 3

## Notes

- Implementation notes
- Decisions made during work
```

### spec.md (optional)

```markdown
# Spec: Feature Name

## Requirements

- Requirement 1
- Requirement 2

## Design

- Design decisions
- API changes
- UI mockups
```

## Naming Conventions

- Track names: `<feature>_<date>` (e.g., `tooltip_fix_20260614`)
- Archive folders: `YYYY-MM-DD` (e.g., `2026-06-30`)
- Metadata status: lowercase (`active`, `completed`)

## Cross-references

- [`docs/HOUSEKEEPING.md`](../docs/HOUSEKEEPING.md) — cleanup rules
- [`docs/adr/ADR-0015-conductor-archival.md`](../docs/adr/ADR-0015-conductor-archival.md) — archival policy
- [`AGENTS.md`](../AGENTS.md) — agent workflow rules
