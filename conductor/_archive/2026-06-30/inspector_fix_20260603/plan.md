# Plan - Fix Skill Inspector Implementation Details Layout

Fix the UI issue where the implementation details in the Skill Inspector exhibit excessive blank space at the top, forcing unnecessary scrolling.

## Objective
Refactor the content cleaning logic and stabilize the QML layout in `SkillInspector.qml` to ensure implementation content is properly trimmed and positioned at the top of its container.

## Key Files & Context
- `src/skill_manager/SkillManagerComponents/SkillInspector.qml`: Main UI component for the skill inspector.
- `src/skill_manager/core/parsing/base.py`: (Reference) Used for understanding how body content is extracted on the backend.

## Implementation Steps

### Step 1: Refactor `cleanBodyContent` logic
Modify `cleanBodyContent` in `SkillInspector.qml` to:
- Use a regex-based approach to strip YAML frontmatter (delimited by `---`).
- Robustly trim leading/trailing whitespace and empty lines.
- Improve stripping of redundant "Name:", "Description:", etc. fields.

### Step 2: Optimize QML Layout
Adjust the implementation details section in `SkillInspector.qml`:
- Remove `Layout.fillHeight: true` from the implementation rectangle to prevent unpredictable expansion.
- Increase `Layout.preferredHeight` from `300` to `400` for better content visibility.
- Ensure `verticalAlignment: Text.AlignTop` is strictly enforced in the `TextArea`.

## Verification & Testing
- **Visual Check**: Open the Skill Inspector for `conductor-implement`, `brainstorming`, and `concise-planning`.
- **Validation**: Confirm the content starts immediately at the top of the box without leading blank space.
- **Regression**: Ensure frontmatter is completely removed and doesn't "leak" into the implementation view.
