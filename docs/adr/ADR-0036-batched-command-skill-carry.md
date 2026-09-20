# ADR-0036: Batched Command Skill Carry

> Status: **Accepted**
> Date: 2026-09-13
> Owner: @DIKKA

## Context

Editing a custom command deployed to several projects fanned out the
write via `update_custom_command_file_multi`, then checked each project
for missing skill dependencies. The old path emitted one
`commandSkillsCarryPrompt` per project into the single-instance
`CommandCarrySkillsDialog`. Each emission overwrote the previous one
(last-writer-wins), so only the last project ever got its missing
skills carried. Multi-project edits silently dropped dependencies.

## Decision

1. **Collect, then emit once**: after the fan-out write and targeted
   rescan, `_collect_missing_skills_batch(pairs, body, tag)` builds one
   entry per project that still misses skills
   (`project_path`, `command_paths`, `missing_skills`), and
   `_emit_missing_skills_batch(batch)` emits exactly one prompt.
2. **Single batched prompt**: multi-project batches travel on the new
   `commandSkillsCarryBatchPrompt(batchJson)` signal; the dialog opens
   via `CommandCarrySkillsDialog.openWithBatch(batch)`, which shows the
   union of missing skills across all projects in one prompt.
3. **Legacy fallback preserved**: a 1-entry batch still uses the legacy
   `commandSkillsCarryPrompt(cmdJson, projPath, skillsJson)` signal, so
   single-project flows are unchanged.
4. **Batch confirm with still-missing filter**:
   `confirmCommandSkillsCarryBatch(batchJson, skillsJson)` re-checks
   each project with `find_missing_skills_for_commands`, keeps only
   confirmed skills still missing per project, then copies per project
   via `copy_commands_with_skill_carry` and rescans.
5. **Idempotent re-edit**: the missing check reads the filesystem, so a
   re-edit after a full carry collects `[]`, emits nothing, and stays
   silent. Applies to both create (`CREATE`) and update (`UPDATE`)
   paths.

## Consequences

### Positive

- Every affected project receives carried skills; no more
  last-writer-wins loss.
- One prompt for multi-project edits: union skill list, one user
  decision, per-project copy.
- Silent no-op re-edit: no nag dialog once dependencies are satisfied.

### Negative

- Two parallel prompt/confirm paths (single + batch) for QML and
  Python to maintain.
- Union list can show a skill already present in one of the projects;
  the still-missing filter trims it at confirm time, not at display.

### Neutral

- Legacy `commandSkillsCarryPrompt` / `confirmCommandSkillsCarry`
  rows stay for the single-project case; no QML caller changes needed.

## Alternatives Considered

### Sequential per-project dialog queue

Rejected: queues one modal per project behind the single dialog
instance. It fixes the data loss but forces N confirm clicks for an
N-project edit and complicates dialog lifetime (queue drain on cancel,
stale entries on rescan). The single union prompt is one decision with
the same per-project copy result.

## References

- `src/skill_manager/controllers/ops/commands.py`
  (`_collect_missing_skills_batch`, `_emit_missing_skills_batch`)
- `src/skill_manager/controllers/ops/copy.py`
  (`confirmCommandSkillsCarryBatch`)
- `src/skill_manager/controllers/ops_controller.py`, `app.py`,
  `app_proxies.py` (batch signal + forwarding)
- `SkillManagerComponents/dialogs/CommandCarrySkillsDialog.qml`
  (`openWithBatch`), `views/LibraryView.qml`, `views/QuickCopyView.qml`
