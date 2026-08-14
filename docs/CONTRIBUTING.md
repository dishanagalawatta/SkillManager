# Contributing

## Workflow

1. **Open a track** under `conductor/tracks/<slug>/` with `plan.md`
   and `metadata.json`. See [conductor/workflow.md](../conductor/workflow.md).
2. **Branch from `develop`** named `track/<slug>`. One track = one branch.
3. **TDD** — red → green → refactor for every change. A track is not
   done until `python scripts/dev_test.py` is green and ruff is clean.
4. **Open a PR to `main`** with the track's spec linked in the
   description. CI must be green before review.
5. **Release** — `uv run python scripts/release.py [bump]` bumps the version,
   creates the release tag, and triggers the CI build. See
   [VERSIONING.md](VERSIONING.md) and [RELEASING.md](RELEASING.md).

## Commit Style

All commits MUST follow [Conventional Commits](https://www.conventionalcommits.org/):

| Prefix | Type | Release Bump | Example |
|---|---|---|---|
| `feat:` | New feature | Minor | `feat: add new view` |
| `fix:` | Bug fix | Patch | `fix: ui alignment` |
| `perf:` | Performance | Patch | `perf: optimize search` |
| `feat!:` | Breaking change | Major | `feat!: redesign API` |
| `docs:`, `test:`, `chore:`, `ci:` | Maintenance | None | `docs: update README` |

Example commits:

```
feat(qml): add glass dropdown component
fix(opfs): handle missing manifest gracefully
perf(search): optimize fuzzy matching
```

## Code Style

- **Python**: ruff (rules in `pyproject.toml`). Line length 100, target
  Python 3.12+. Run `uv run ruff check . --fix` and `uv run ruff format .`
  before committing.
- **QML**: 4-space indent. No QObject-derived children of `QQuickItem`
  (see [ADR-0003](https://github.com/dishanagalawatta/SkillManager/blob/main/ADR_INDEX.md#adr-0003)).
  All shared components live in `src/skill_manager/SkillManagerComponents/`.
- **Imports**: Use absolute imports rooted at `skill_manager.`. No
  relative imports past one level.

## Pull Request Checklist

- [ ] `python scripts/dev_test.py` (or `uv run pytest -n auto`) is green locally
- [ ] `uv run ruff check src tests` and `uv run ruff format --check src tests` are clean
- [ ] New `AppController` surface is documented in `docs/API.md`
- [ ] New environment variables are documented in `docs/ENVIRONMENT.md`
- [ ] Architectural changes are reflected in `ADR_INDEX.md` and include Mermaid diagrams
- [ ] No secrets in the diff (`.env` is git-ignored — never commit it)
- [ ] Commit messages follow [Conventional Commits](https://www.conventionalcommits.org/)

## Test Requirements

| Layer | Coverage expectation |
|-------|---------------------|
| `core/` (business logic) | 100% line + branch |
| `controllers/` | 100% line + branch |
| QML components | Loading smoke tests in `tests/qml/` |
| UI flows | One `pytest-qt` test per user-visible flow |

## Release Process

Releases are orchestrated using `uv run python scripts/release.py [patch|minor|major]`.
See [RELEASING.md](RELEASING.md) for the full process.

## Security

Report vulnerabilities by opening a private security advisory on
GitHub. Do not open a public issue.

## Code of Conduct

Be kind, assume good faith, focus on the work. Disagreement about
*what* to do is welcome; disrespect about *who* is doing it is not.
