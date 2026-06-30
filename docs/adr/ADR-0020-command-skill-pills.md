# ADR-0020: Command Inspector Skill-Dependency Pills

> Status: **Accepted**
> Date: 2026-06-14
> Owner: @DIKKA

## Context

The Command Inspector panel shows command details (name, prompt, description). Users needed to understand which skills a command depends on, but this information was buried in the command's YAML frontmatter.

## Decision

Expose skill dependencies as **clickable pills** in the Command Inspector:

### UI Changes

- `CommandInspector.qml`: Add horizontal flow of skill-reference pills below the command description
- Each pill shows the skill name with an always-on body highlight
- Clicking a pill navigates to the skill in the Library view
- Pills use `SkillRefHighlighter` for consistent styling

### Data Flow

```
Command YAML frontmatter
  └─▶ skill_references.py  (parse "skills" field)
        └─▶ CommandInspector.qml  (render pills)
              └─▶ UIController.selectSkill(skillId)  (on click)
```

### Highlighting

- `skill_ref_highlighter.py`: Regex-based skill name detection
- Always-on body highlights for skill names in command text
- Consistent with `SkillItem.qml` highlighting

## Consequences

### Positive

- Users can immediately see skill dependencies in commands
- One-click navigation from command → skill
- Visual consistency with existing skill reference highlighting

### Negative

- Slight UI complexity increase in CommandInspector
- Requires skill references to be parsed from YAML frontmatter

### Neutral

- `test_command_referenced_skills_pills.py` covers the feature
- Pill styling follows `Theme.qml` tokens (no hardcoded values)

## Alternatives Considered

### Show as plain text list

Rejected — no navigation, no visual distinction from other text.

### Tooltip on hover

Rejected — discoverability issue; pills are always visible.

## References

- [`src/skill_manager/SkillManagerComponents/CommandInspector.qml`](../../src/skill_manager/SkillManagerComponents/CommandInspector.qml)
- [`src/skill_manager/core/skill_references.py`](../../src/skill_manager/core/skill_references.py)
- [`tests/test_command_referenced_skills_pills.py`](../../tests/test_command_referenced_skills_pills.py)
