# SkillManager

> A professional desktop tool for managing reusable agent skills across repositories.

[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://python.org)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-1.8.0-orange.svg)](pyproject.toml)

## Overview

SkillManager is an enterprise-grade agent skill orchestration system. It provides a native desktop UI for discovering, organizing, and deploying reusable skills across multiple AI coding agents (opencode, Claude Code, Codex, Gemini CLI, etc.).

## Tech Stack

| Layer | Technology | Version |
|-------|-----------|----------|
| UI Framework | PySide6 / Qt 6 (QML) | ≥ 6.7 |
| Language | Python | ≥ 3.12 |
| Package Manager | [uv](https://github.com/astral-sh/uv) | any |
| Parallelism | joblib | ≥ 1.4 |
| Caching | diskcache | any |
| Config | pydantic-settings | ≥ 2.14 |
| Telemetry | PostHog + Sentry | opt-in |
| Schema Validation | pydantic v2 | ≥ 2.0 |
| Search | rapidfuzz | any |
| HTTP | httpx | any |
| Linter / Formatter | ruff | any |
| Test Runner | pytest + pytest-qt | any |

## Prerequisites

Before installing, ensure these are available on your system:

```bash
# Python 3.12 or newer
python --version  # → Python 3.12.x

# uv package manager
curl -LsSf https://astral.sh/uv/install.sh | sh
uv --version  # → uv x.y.z

# Qt 6 platform plugins (Linux only)
sudo apt install -y libglib2.0-0 libxcb-cursor0 libxkbcommon-x11-0
```

> On **macOS** and **Windows**, Qt plugins are bundled with PySide6 via `uv sync`. No extra step needed.

## Features

- **Deep QML/PySide6 integration** — buttery-smooth native UI with custom glass components, dark mode, and animated transitions
- **True multiprocessing** — heavy parsing and discovery run on `joblib.Parallel` to keep the PySide6 event loop responsive
- **Background discovery & caching** — silent cache refreshes, file watcher, and fingerprint-based incremental scans
- **Quick Copy** — one-click deploy skills to any configured project target
- **Screenshot capture** — built-in screen annotation tool with tools, undo/redo, and export
- **Skill packages** — manage multiple skill sources with versioning and auto-updates
- **Global hotkey** — summon the UI from anywhere with a configurable keyboard shortcut (`ctrl+shift+s` default)
- **MCP Server** — agent-native stdio interface for headless skill management
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

**Key environment variables:**

| Variable | Default | Purpose |
|----------|---------|----------|
| `SKILL_MANAGER_LOG_LEVEL` | `INFO` | Log verbosity (`DEBUG`/`INFO`/`WARNING`/`ERROR`) |
| `SKILL_MANAGER_HOTKEY` | `ctrl+shift+s` | Global hotkey to summon the UI |
| `SKILL_MANAGER_DIAG` | — | Set `1` to enable shutdown diagnostics logging (debug only) |
| `QT_QPA_PLATFORM` | native | Set `offscreen` for headless/CI |
| `POSTHOG_PROJECT_TOKEN` | — | PostHog analytics token (opt-in) |
| `SENTRY_DSN` | — | Sentry error tracking DSN (opt-in) |

See [`environments/README.md`](environments/README.md) for tier-specific configs (dev, staging, prod) and [`docs/ENVIRONMENT.md`](docs/ENVIRONMENT.md) for the full variable reference.

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

### MCP Server for Agents

SkillManager ships a native Python MCP server (stdio, via the `mcp` SDK) that lets AI agents search, read, create, update, deploy, delete, and analyze skills without opening a GUI.

- **Read-Only Mode**: `uv run skill-manager --mcp` (`sm_list_skills`, `sm_get_skill`, `sm_search_skills`, `sm_sync_skills`, build, analyze, monitor, debug)
- **Write Mode**: `uv run skill-manager --mcp --mcp-allow-write` (adds `sm_create_skill`, `sm_update_skill`, `sm_deploy`, `sm_delete_skill`)

See [docs/MCP_SERVER.md](docs/MCP_SERVER.md) for full tool reference and client setup guides for **Claude Desktop**, **Cursor**, **VS Code / Continue**, **Antigravity**, **Goose**, **Windsurf**, and **OpenCode**.

## Building

```bash
# PyInstaller build (preferred — runs inside venv automatically)
uv run skill-manager-build

# Or directly (auto-relaunches under venv if needed)
python scripts/build_app.py

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

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `Could not load Qt platform plugin "xcb"` | `export QT_QPA_PLATFORM=offscreen` then re-run |
| `ModuleNotFoundError: No module named 'PySide6'` | `uv sync` then retry |
| App doesn't start after build | Run with `uv run skill-manager` (not direct Python) |
| Global hotkey not working | Check `SKILL_MANAGER_HOTKEY` in `.env`; default is `ctrl+shift+s` |
| Tests failing with `QML module not found` | Set `QML_DISABLE_DISK_CACHE=1 QT_QPA_PLATFORM=offscreen` before running tests |

For more, see [`environments/README.md`](environments/README.md) and [`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md).

## Release Strategy

Releases are managed by `python-semantic-release` via commit message keywords:

| Commit Keyword | Release Type | Example |
|----------------|-------------|----------|
| `feat:` | Minor | `feat: add bulk skill export` |
| `fix:` | Patch | `fix: correct filter state reset` |
| `feat!:` / `BREAKING CHANGE` | Major | `feat!: new config schema` |
| `chore:` / `docs:` / `refactor:` | No release | `docs: update README` |

See [`docs/RELEASING.md`](docs/RELEASING.md) for the full release checklist.

## License

MIT License — see [LICENSE](LICENSE).

## Contributing

See [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md).
