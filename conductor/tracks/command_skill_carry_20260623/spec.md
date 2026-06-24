# Spec — Command–skill carry on copy

> See [`ADR-0017`](../../ADR_INDEX.md#adr-0017-command-skill-carry)
> for the authoritative design decision.

## Summary

When copying commands to a project, detect skill dependencies and
offer to carry missing skills alongside the commands.

## Components

1. **`core/skill_references.py`** — Pure function: extract skill name
   candidates from command markdown bodies using the same regex as
   `replace_skill_references_in_command`.

2. **`core/copier.py`** — `find_missing_skills_for_commands()` compares
   extracted names against target project's installed skills.

3. **`controllers/ops_controller.py`** — `copyCommandsToProjectWithCarry()`
   emits `commandSkillsCarryPrompt` signal when skills are missing.

4. **`dialogs/CommandCarrySkillsDialog.qml`** — Per-skill toggle
   checklist with "Carry All" / "Copy Commands Only" buttons.

## Diagnostic Events

| Event | Category |
|-------|----------|
| Prompt shown | `CATEGORY_COMMAND_CARRY_PROMPTED` |
| Skills copied | `CATEGORY_COMMAND_CARRY_COPIED` |
| Skills skipped | `CATEGORY_COMMAND_CARRY_SKIPPED` |
