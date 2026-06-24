# Agent Instructions
> Generated via /agents-md

## Core Constraints
- **Strictly exclude** `TODO.md`, `.agents/commands`, and `.agents/skills` from cleanup or modification.
- Always run `uv run python -m skill_manager.__main__` for development.
- Respect the QML lifecycle: clear `cacheBuffer` before setting `model = null` to prevent incubation destruction exceptions.
