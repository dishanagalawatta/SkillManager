# Plan — Command–skill carry on copy

> Formalizes the in-flight work implementing ADR-0017.
> Tracks untracked files: `core/skill_references.py`,
> `dialogs/CommandCarrySkillsDialog.qml`, `tests/test_carry_skills.py`,
> `tests/test_skill_references.py`.

## Scope

- In: Skill reference extraction, carry dialog, copy-with-carry workflow.
- Out: Changes to `.agents/skills/` (excluded by AGENTS.md).

## Action Items

- [x] Step 1: Core module — `core/skill_references.py` (extract + resolve)
- [x] Step 2: Dialog — `dialogs/CommandCarrySkillsDialog.qml`
- [x] Step 3: Tests — `tests/test_carry_skills.py`, `tests/test_skill_references.py`
- [x] Step 4: API docs — `docs/API.md` § 6 (signals)
- [ ] Step 5: Validation — `python run_tests.py` → 0 failures, lint clean
- [ ] Step 6: Commit + push to `track/command_skill_carry_20260623`

## Open Questions

- None — design locked by ADR-0017.
