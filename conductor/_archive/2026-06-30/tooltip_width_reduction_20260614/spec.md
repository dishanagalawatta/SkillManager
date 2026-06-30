# Tooltip Width Reduction

## Description
Reduce the maximum horizontal length (width) of tooltips in `SkillItem.qml` to make them more compact and less intrusive.

## Requirements
- Reduce `implicitWidth` limit for screenshot preview from 400 to 300.
- Reduce `width` limit for text preview from 400 to 280.
- Adjust truncation character limit to match the smaller width (e.g., from 250 to 180).

## Architecture Constraints
- Edit `src/skill_manager/SkillManagerComponents/SkillItem.qml`.
- Ensure tooltips remain legible and useful despite the smaller size.