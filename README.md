# SkillManager

<p align="center">
  <img src="assets/brand/logo.png" width="128" height="128" alt="SkillManager Logo">
  <br>
  <b>A professional workspace to manage, sync, and deploy your AI agent skills.</b>
</p>

<p align="center">
  <a href="https://github.com/dishanagalawatta/SkillManager/actions/workflows/ci.yml"><img src="https://github.com/dishanagalawatta/SkillManager/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://github.com/dishanagalawatta/SkillManager/actions/workflows/release.yml"><img src="https://github.com/dishanagalawatta/SkillManager/actions/workflows/release.yml/badge.svg" alt="Release"></a>
</p>

---

## Overview & Demo

<video src="https://github.com/user-attachments/assets/29541600-3647-474d-8a3e-98160cdd37ff" controls="controls" muted="muted" style="max-height:640px;"></video>
*Watch the 3-minute overview of SkillManager directly inline.*

---

## Key Features

SkillManager is designed for developers who need to manage growing libraries of AI skills across dozens of project repositories.

- **Quick Copy Workflow**: Instantly browse project-specific skills and copy formatted references directly to your clipboard.
- **Surgical Sync**: Intelligent synchronization that updates outdated skills across multiple repositories without full rescans.
- **Secure Auto-Update**: Background application updates powered by TUF (The Update Framework) for robust and secure delivery.
- **Screenshot & Redaction**: Capture screenshots with PII redaction capabilities for AI context.
- **Centralized Library**: A single, searchable hub for all your markdown-based AI skills.
- **Modern UI**: Hardware-accelerated "Solid Matte & Liquid Glass" interface built with PySide6/QML.
- **Zero-Config Entry**: Professional installers for Windows, macOS, and Linux.

---

## Quick Start (Developers)

```bash
# 1. Install dependencies
uv sync

# 2. Run the app
uv run skill-manager

# 3. Run the full test suite
python run_tests.py
```

The full local-dev loop, debugging recipes, and PySide6/QML cache
invalidation steps live in [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md).

---

## Visual Showcase

### The Central Library

Manage thousands of skills with ease. Filter by category, search instantly, and preview content in a high-fidelity editor.
![Library View](assets/readme/SkillManager_Library.png)

### Quick Copy Integration

The ultimate developer companion. Keep your most-used skills just a click away while working in your IDE.
![Quick Copy](assets/readme/SkillManager_QuickCopy.png)

### Premium Design

Native Windows 11 integration (Mica/Acrylic) and a custom "Liquid Glass" design system provide a focused, distraction-free environment.
![UI Mockup](assets/readme/SkillManager_UI_mockup.jpeg)

---

## Getting Started

### For End Users

You don't need Python or any developer tools to use SkillManager.

1. Visit the **[Releases](https://github.com/dishanagalawatta/SkillManager/releases)** page.
2. Download the installer for your OS:
   - **Windows**: `SkillManager_Setup.exe`
   - **macOS**: `SkillManager_Portable_macos.zip`
   - **Linux**: `SkillManager_Portable_linux.zip`
3. Install and launch!

### For Developers

If you want to contribute or build from source, see the
**[Development Guide](docs/DEVELOPMENT.md)**, then the
**[Contributing Guide](docs/CONTRIBUTING.md)** for PR conventions and
release tagging.

---

## Documentation

| Audience | Document | Purpose |
|----------|----------|---------|
| User | [User Guide](docs/USER_GUIDE.md) | End-user manual |
| Engineer | [Architecture](docs/ARCHITECTURE.md) | Module map, lifecycle, data flow |
| Engineer | [API Reference](docs/API.md) | `AppController` Q_PROPERTY / Slot / Signal surface |
| Engineer | [Environment](docs/ENVIRONMENT.md) | Every environment variable |
| Engineer | [Development](docs/DEVELOPMENT.md) | Local-dev loop, debugging |
| Engineer | [Categories](docs/CATEGORIES.md) | Skill taxonomy and parser rules |
| Engineer | [Versioning](docs/VERSIONING.md) | Release trigger rules |
| Engineer | [Releasing](docs/RELEASING.md) | Release lifecycle guide |
| Contributor | [Contributing](docs/CONTRIBUTING.md) | PR + commit + review rules |
| Decision | [ADR Index](ADR_INDEX.md) | All architecture decisions |
| Agent | [AGENTS.md](AGENTS.md) | Agent-facing instructions (concise) |
| Designer | [Design](DESIGN.md) | "Solid Matte & Liquid Glass" system |
| Planner | [conductor/workflow.md](conductor/workflow.md) | Track lifecycle |

---

## Quality Gates

| Gate | Command | Source |
|------|---------|--------|
| Lint | `uv run ruff check .` | ruff config in `pyproject.toml` |
| Format | `uv run ruff format .` | ruff config in `pyproject.toml` |
| Test | `uv run pytest` | `pyproject.toml` `[tool.pytest.ini_options]` |
| Full Suite | `python run_tests.py` | Sequential + parallel + lint |
| QML Diagnostic | `uv run pytest tests/test_qml_comprehensive_diagnostic.py` | `tests/test_qml_comprehensive_diagnostic.py` |

CI runs all of the above. A PR is mergeable only when all five pass.

---

## License

[**MIT License**](LICENSE)

Copyright (c) 2026 Don Dishan Kanchuka Agalawatta
