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

## Canonical Metadata Schema

All `metadata.json` files must use these exact field names (inconsistencies
found in older tracks have been documented here for normalization):

```json
{
  "slug":        "<track-name>",       // REQUIRED. Kebab-case identifier
  "title":       "Human-readable title", // REQUIRED. ≤ 60 chars
  "status":      "active",             // REQUIRED. One of: active | completed
  "owner":       "@username",          // REQUIRED
  "created":     "YYYY-MM-DD",         // REQUIRED. ISO 8601 date
  "completed":   "YYYY-MM-DD",         // Set when status → completed
  "description": "What this implements", // REQUIRED. 1–2 sentences
  "related_adrs": ["ADR-00XX"],        // Optional. List of related ADR IDs
  "notes":       "Free-form text"      // Optional. Work-in-progress notes
}
```

> **Deprecated fields** (found in legacy tracks, do not use in new tracks):
> `id` (use `slug`), `type` (not part of schema), `current_phase`, `current_task`,
> `phases`, `tasks`, `commits` (use git log instead), `branch`, `updated`.

## Stale Track Policy

A track is considered **stale** when it has had no commits, plan updates,
or metadata changes in **30 or more days** and its status is still `active`.

**Monthly review checklist** (first Monday of each month):

1. Run: `find conductor/tracks -name 'metadata.json' -mtime +30`
2. For each stale track, check if the associated branch still exists:
   ```bash
   git branch --list "track/<slug>"
   ```
3. If the branch is merged or deleted → update status to `completed` and archive
4. If work is genuinely paused → add a `notes` field with reason and target date
5. If track is abandoned → discuss with owner before archiving as `completed`

## Agent Integration

When AI agents interact with conductor tracks, they must follow these rules:

- **Reading**: Always read `metadata.json` and `plan.md` before starting work
- **Updating plan.md**: Use `[ ]` → `[/]` (in progress) → `[x]` (done) notation
- **Updating metadata.json**: Update `status` when all tasks are complete
- **Archiving**: Use `/conductor-manage` skill — never manually `mv` without updating the index
- **Creating new tracks**: Follow the Metadata Schema above exactly; avoid deprecated fields
- **Halting**: If a plan step fails, halt and report — do not skip steps silently

## Cross-references

- [`docs/HOUSEKEEPING.md`](../docs/HOUSEKEEPING.md) — cleanup rules
- [`docs/adr/ADR-0015-conductor-archival.md`](../docs/adr/ADR-0015-conductor-archival.md) — archival policy
- [`docs/adr/ADR-0022-workspace-cleanup-standardization.md`](../docs/adr/ADR-0022-workspace-cleanup-standardization.md) — gitignore and archival batch
- [`AGENTS.md`](../AGENTS.md) — agent workflow rules
