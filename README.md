# SkillManager

> A professional workspace to manage, sync, and deploy AI agent skills
> across multiple project repositories. Windows desktop · PySide6 /
> QML · Python 3.12+.

## Features

- **Quick Copy** — browse project skills, copy formatted references.
- **Surgical Sync** — update only outdated skills across repos.
- **App Update** — background version checks via GitHub Releases API.
- **Screenshot & Redact** — capture screenshots with PII redaction.
- **Central Library** — single, searchable hub for skill metadata.
- **Liquid Glass UI** — hardware-accelerated, native Windows 11 shell.

## Quick Start

```bash
uv sync
uv run skill-manager
python run_tests.py
```

## End-User Install

Download `SkillManager_Setup.exe` from
[Releases](https://github.com/dishanagalawatta/SkillManager/releases).
No Python required.

## Documentation

| Audience | Document | Purpose |
|----------|----------|---------|
| Everyone | [README.md](README.md) | This file. |
| User | [docs/USER_GUIDE.md](docs/USER_GUIDE.md) | End-user manual. |
| Engineer | [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Module map, lifecycle. |
| Engineer | [docs/API.md](docs/API.md) | `AppController` surface. |
| Engineer | [docs/ENVIRONMENT.md](docs/ENVIRONMENT.md) | Every env var. |
| Engineer | [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) | Local-dev loop. |
| Engineer | [docs/CATEGORIES.md](docs/CATEGORIES.md) | Skill taxonomy. |
| Engineer | [docs/VERSIONING.md](docs/VERSIONING.md) | Release triggers. |
| Engineer | [docs/RELEASING.md](docs/RELEASING.md) | Release lifecycle. |
| Engineer | [docs/CI_CD.md](docs/CI_CD.md) | Pipelines. |
| Contributor | [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md) | PR + commit rules. |
| Decision | [ADR_INDEX.md](ADR_INDEX.md) | Architecture decisions. |
| Agent | [AGENTS.md](AGENTS.md) | Agent instructions. |
| Designer | [DESIGN.md](DESIGN.md) | Design system. |
| Planner | [conductor/workflow.md](conductor/workflow.md) | Track lifecycle. |

## Quality Gates

| Gate | Command |
|------|---------|
| Lint | `uv run ruff check .` |
| Format | `uv run ruff format .` |
| Test | `uv run pytest` |
| Full Suite | `python run_tests.py` |
| QML Diagnostic | `uv run pytest tests/test_qml_comprehensive_diagnostic.py` |

A PR is mergeable only when all five pass.

## License

[MIT](LICENSE) — Copyright (c) 2026 Don Dishan Kanchuka Agalawatta.
