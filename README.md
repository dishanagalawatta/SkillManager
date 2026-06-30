# SkillManager

> A professional desktop tool for managing reusable agent skills across repositories.

[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://python.org)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-1.8.0-orange.svg)](pyproject.toml)

## Overview

SkillManager is an enterprise-grade agent skill orchestration system. It provides a native desktop UI for discovering, organizing, and deploying reusable skills across multiple AI coding agents (opencode, Claude Code, Codex, Gemini CLI, etc.).

## Features

- **Deep QML/PySide6 integration** — buttery-smooth native UI with custom glass components, dark mode, and animated transitions
- **True multiprocessing** — heavy parsing and discovery run on `joblib.Parallel` to keep the PySide6 event loop responsive
- **Background discovery & caching** — silent cache refreshes, file watcher, and fingerprint-based incremental scans
- **Quick Copy** — one-click deploy skills to any configured project target
- **Screenshot capture** — built-in screen annotation tool with tools, undo/redo, and export
- **Skill packages** — manage multiple skill sources with versioning and auto-updates
- **Global hotkey** — summon the UI from anywhere with a configurable keyboard shortcut
- **Diagnostics** — structured telemetry for debugging and usage analytics

## Quickstart

```bash
# Clone
git clone https://github.com/dishanagalawatta/SkillManager.git
cd SkillManager

# Install dependencies
uv sync

# Run
uv run skill-manager
# or
uv run python -m skill_manager.__main__
```

## Configuration

Copy `.env.example` to `.env` and fill in your tokens (PostHog, Sentry):

```bash
cp .env.example .env
```

See [`environments/README.md`](environments/README.md) for tier-specific configs (dev, staging, prod).

## Development

```bash
# Lint
uv run ruff check src tests --fix

# Format
uv run ruff format src tests

# Tests (parallel)
uv run pytest -n auto --dist loadfile

# Run all checks
python scripts/dev_test.py
```

See [`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md) for full development guide.

## Building

```bash
# PyInstaller build
uv run python scripts/build_app.py

# Inno Setup installer (Windows)
# See packaging/windows/installer.iss
```

See [`docs/RELEASING.md`](docs/RELEASING.md) for release workflow.

## Documentation

| Document | Description |
|----------|-------------|
| [docs/INSTALL.md](docs/INSTALL.md) | Installation instructions |
| [docs/USER_GUIDE.md](docs/USER_GUIDE.md) | End-user manual |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | System architecture & data flow |
| [docs/API.md](docs/API.md) | QML/Python API reference |
| [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) | Developer setup & conventions |
| [docs/CI_CD.md](docs/CI_CD.md) | CI/CD pipeline reference |
| [docs/RELEASING.md](docs/RELEASING.md) | Release checklist & versioning |
| [docs/ENVIRONMENT.md](docs/ENVIRONMENT.md) | Environment variable reference |
| [docs/SECURITY.md](docs/SECURITY.md) | Security policy & token handling |
| [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md) | Contribution guidelines |
| [docs/VERSIONING.md](docs/VERSIONING.md) | Semantic versioning policy |
| [docs/CATEGORIES.md](docs/CATEGORIES.md) | Skill categorization system |
| [docs/HOUSEKEEPING.md](docs/HOUSEKEEPING.md) | Workspace cleanup rules |
| [docs/PRODUCT_TELEMETRY.md](docs/PRODUCT_TELEMETRY.md) | PostHog/Sentry integration |
| [ADR_INDEX.md](ADR_INDEX.md) | Architecture Decision Records |

## Architecture

SkillManager follows a layered architecture:

```
┌─────────────────────────────────────────┐
│  QML UI Layer (SkillManagerComponents/) │
├─────────────────────────────────────────┤
│  Controllers (app.py, controllers/)     │
├─────────────────────────────────────────┤
│  Core Logic (core/)                     │
├─────────────────────────────────────────┤
│  Utils (utils/)                         │
└─────────────────────────────────────────┘
```

See [`DESIGN.md`](DESIGN.md) for detailed design patterns and [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for full architecture.

## Project Structure

```
SkillManager/
├── src/skill_manager/          # Application source
│   ├── core/                   # Business logic, models, parsing
│   ├── controllers/            # PySide6 controller layer
│   ├── utils/                  # Threading, platform utils
│   └── SkillManagerComponents/ # QML UI components
├── tests/                      # Test suite (pytest)
├── scripts/                    # Dev scripts, diagnostics
├── packaging/                  # Build & installer configs
├── environments/               # Tier-specific env examples
├── conductor/                  # Track management (active & archived)
├── docs/                       # Documentation
├── assets/                     # Brand, UI icons, README images
└── data/                       # Runtime state (gitignored)
```

## License

MIT License — see [LICENSE](LICENSE).

## Contributing

See [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md).
