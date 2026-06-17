# Contributing

## Workflow

1. **Open a track** under `conductor/tracks/<slug>/` with `plan.md`
   and `metadata.json`. See [conductor/workflow.md](../conductor/workflow.md).
2. **Branch from `develop`** named `track/<slug>`. One track = one branch.
3. **TDD** — red → green → refactor for every change. A track is not
   done until `python run_tests.py` is green and ruff is clean.
4. **Open a PR to `develop`** with the track's spec linked in the
   description. CI must be green before review.
5. **Merge** with a release trigger in the squash-merge commit message
   (`[patch]`, `[minor]`, `[major]`, or `[dev]`). See
   [VERSIONING.md](VERSIONING.md).

## Commit Style

Conventional Commits, plus a release trigger token. Examples:

```
feat(qml): add glass dropdown component [minor]
fix(opfs): handle missing manifest gracefully [patch]
chore(deps): bump pyside6 to 6.11.1 [dev]
```

Release triggers are matched case-sensitively, on a single line, anywhere
in the commit message. Commits without a trigger are merged without
bumping the version.

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

- [ ] `python run_tests.py` is green locally
- [ ] `uv run ruff check .` and `uv run ruff format --check .` are clean
- [ ] `uv run pytest tests/test_qml_comprehensive_diagnostic.py` is green
- [ ] New `AppController` surface is documented in `docs/API.md`
- [ ] New environment variables are documented in `docs/ENVIRONMENT.md`
- [ ] Architectural changes are reflected in `ADR_INDEX.md`
- [ ] No secrets in the diff (`.env` is git-ignored — never commit it)
- [ ] Commit messages include a release trigger token

## Test Requirements

| Layer | Coverage expectation |
|-------|---------------------|
| `core/` (business logic) | 100% line + branch |
| `controllers/` | 100% line + branch |
| QML components | Loading smoke test in `tests/test_qml_comprehensive_diagnostic.py` |
| UI flows | One `pytest-qt` test per user-visible flow |

## Release Process

Releases are produced by the CI release pipeline, not by hand. The
release commit on `main` is the one that contains the trigger token.
Never push a version tag manually.

## Security

Report vulnerabilities by opening a private security advisory on
GitHub. Do not open a public issue.

## Code of Conduct

Be kind, assume good faith, focus on the work. Disagreement about
*what* to do is welcome; disrespect about *who* is doing it is not.
