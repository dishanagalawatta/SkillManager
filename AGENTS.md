# Agent Instructions

> This file defines constraints, conventions, and workflows for AI agents
> and human contributors working on SkillManager. Keep it concise.

## Core Constraints

### Exclusions (never modify)

| Path | Reason |
|------|--------|
| `TODO.md` | User-managed task list |
| `.agents/commands/**` | User-managed agent commands |
| `.agents/skills/**` | Installed agent skills |
| `image/TODO/**` | Packaging reference screenshots |

### Mandatory Rules

1. **Entry point**: Always use `uv run python -m skill_manager.__main__` for development.
2. **QML lifecycle**: Clear `cacheBuffer` before setting `model = null` to prevent incubation destruction exceptions.
3. **Threading**: Never block the PySide6 event loop. Heavy work runs on `joblib.Parallel` or `BackgroundTaskRunner`.
4. **Telemetry**: Never log or commit API tokens. `.env` is gitignored.

## Conventions

### Code Style

- **Lint**: `uv run ruff check src tests` — must pass before commit
- **Format**: `uv run ruff format src tests` — must pass before commit
- **Type hints**: Use `pyright` with `.pyrightconfig.json` settings
- **QML**: Follow `Theme.qml` semantic tokens; no hardcoded colors/sizes

### Testing

- **Framework**: pytest + pytest-qt + pytest-cov
- **Parallel**: `uv run pytest -n auto --dist loadfile`
- **Coverage**: Target 90% (`fail_under = 90` in `pyproject.toml`)
- **Run all checks**: `python scripts/dev_test.py`

### Git & Commits

- Use [Conventional Commits](https://www.conventionalcommits.org/) format
- Prefix: `feat:`, `fix:`, `refactor:`, `test:`, `chore:`, `docs:`
- Keep subject line ≤ 50 characters
- Body only when "why" isn't obvious from subject

## Workflow

### Before Any Edit

1. Run `uv run ruff check src tests` to verify baseline
2. Check `docs/HOUSEKEEPING.md` for cleanup rules
3. Review related ADRs in `docs/adr/` if changing architecture

### After Any Edit

1. Run `uv run ruff check src tests --fix`
2. Run `uv run ruff format src tests`
3. Run `uv run pytest tests/test_<relevant>.py` (smoke subset)
4. Verify `git status` shows no unexpected untracked files

### Conductor Tracks

- Active tracks live in `conductor/tracks/<name>/`
- Each track has `metadata.json`, `plan.md`, and optionally `spec.md`
- When a track is fully merged, archive it to `conductor/_archive/<date>/`
- See [`conductor/workflow.md`](conductor/workflow.md) for full lifecycle

### ADR Process

- New architectural decisions → create `docs/adr/ADR-XXXX-<slug>.md`
- Update `ADR_INDEX.md` with entry
- See [`docs/adr/0000-template.md`](docs/adr/0000-template.md) for format

## Forbidden Actions

- Never commit `.env`, `data/*.json`, or `src/data/*.json`
- Never modify `TODO.md`, `.agents/commands/`, `.agents/skills/`
- Never hardcode colors, sizes, or fonts in QML (use `Theme.qml` tokens)
- Never use `ThreadPoolExecutor` for heavy work (use `joblib.Parallel`)
- Never block the main thread with I/O or computation

## Quick Reference

| Task | Command |
|------|---------|
| Run app | `uv run skill-manager` |
| Lint | `uv run ruff check src tests` |
| Format | `uv run ruff format src tests` |
| Test (parallel) | `uv run pytest -n auto` |
| Test (single file) | `uv run pytest tests/test_config.py` |
| All checks | `python scripts/dev_test.py` |
| Build | `uv run python scripts/build_app.py` |

## Cross-references

- [`docs/HOUSEKEEPING.md`](docs/HOUSEKEEPING.md) — cleanup rules
- [`conductor/workflow.md`](conductor/workflow.md) — track lifecycle
- [`docs/CONTRIBUTING.md`](docs/CONTRIBUTING.md) — contribution guidelines
- [`ADR_INDEX.md`](ADR_INDEX.md) — architecture decisions
