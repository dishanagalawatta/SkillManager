# SkillManager

A professional desktop application for managing, syncing, and deploying reusable AI agent skills across multiple project repositories. Built with a **Solid Matte & Liquid Glass** aesthetic, it provides a high-performance, immersive workspace for developers.

---

## ✨ Key Features

- **🚀 Quick Copy Workflow**: Instantly browse project-specific skills and copy formatted references directly to your clipboard using client-specific templates (Antigravity, Gemini CLI, etc.).
- **📚 Centralized Library**: Manage all your markdown-based AI skills in one central location with full-text search and category filtering.
- **🔄 Surgical Sync**: Intelligent synchronization engine that identifies and updates outdated skills across multiple project repositories without full rescans.
- **🎨 Modern UI**: Hardware-accelerated interface built with PySide6/QML, featuring native Windows 11 styling (Mica/Acrylic) and a premium design system.
- **📦 Cross-Platform**: Optimized standalone executables for Windows, macOS, and Linux.

---

## 🛠️ Tech Stack

- **Language**: Python 3.12+
- **GUI Framework**: PySide6 (Qt 6.8+) with QML for declarative UI
- **Dependency Management**: `uv` (Ultra-fast Python package installer)
- **Linting & Formatting**: `ruff`
- **Packaging**: PyInstaller & Inno Setup
- **Testing**: `pytest`
- **Automated Releases**: `python-semantic-release`

---

## 🎨 Design System

SkillManager follows the **Solid Matte & Liquid Glass** design guide. It balances the stability of solid, deeply-tinted materials with the depth of frosted glass components.

- **Solid Matte Foundation**: Deeply-tinted material (`#0E1210`) eliminates desktop wallpaper bleed-through.
- **Liquid Glass Pills**: Functional areas are encapsulated in frosted glass containers with 1px reflection borders.
- **Mica/Acrylic Integration**: Native shell effects on Windows for an immersive OS-native feel.

For full details on the design philosophy and layer structure, see **[DESIGN.md](DESIGN.md)**.

---

## 🚀 Getting Started (End Users)

If you just want to use the application, you do not need to install Python. Head over to the [Releases](https://github.com/yourusername/SkillManager/releases) page and download the installer for your operating system.

- **Windows**: Download `SkillManager_Setup.exe` (Installer) or `SkillManager_Portable_windows.zip`.
- **macOS**: Download `SkillManager_Portable_macos.zip` (Portable executable).
- **Linux**: Download `SkillManager_Portable_linux.zip`.
- **Source Code**: Automatically provided by GitHub as `.zip` and `.tar.gz` archives.

*Note: Since the executables are not currently code-signed, you may need to click "Run anyway" (Windows SmartScreen) or "Right-click -> Open" (macOS Gatekeeper).*

---

## 💻 Local Development

### 1. Prerequisites

- Python 3.12 or higher
- [uv](https://astral.sh/uv) (Ultra-fast Python package installer)
- Git

### 2. Clone the Repository

```bash
git clone https://github.com/yourusername/SkillManager.git
cd SkillManager
```

### 3. Install Dependencies

Using `uv`, sync the environment and dependencies (this automatically creates a `.venv`):

```bash
uv sync
```

### 4. Run the Application

Launch the app directly from source without building the executable:

```bash
uv run skill-manager
# OR
uv run python -m skill_manager
```

---

## 🏗️ Architecture

SkillManager is built on a **Hub and Spoke** modular architecture to ensure scalability and maintainability.

### Directory Structure

```text
├── assets/          # Branding, icons, and static assets
├── docs/            # Detailed technical documentation
├── packaging/       # PyInstaller specs and Inno Setup scripts
├── scripts/         # Automation scripts (e.g., build_app.py)
├── src/
│   └── skill_manager/
│       ├── controllers/       # Sub-controllers (UI, Config, Ops)
│       ├── core/              # Domain logic (parsing, discovery, syncing)
│       ├── models/            # Data structures
│       ├── SkillManagerComponents/ # QML UI layer
│       ├── app.py             # Main AppController (The Hub)
│       └── __main__.py        # Entry point
└── tests/           # Pytest suite
```

### Key Components

- **`AppController` (The Hub)**: The main entry point and QML bridge. It coordinates between specialized sub-controllers.
- **Sub-Controllers**:
    - `UIController`: Manages window geometry, theme state, and asset resolution.
    - `ConfigController`: Handles source/project configuration and `config.json` persistence.
    - `OpsController`: Encapsulates skill operations like copying, deletion, and archiving.
    - `UpdateController`: Orchestrates background synchronization and update state tracking.

For an in-depth look at the architecture, data flow, and QML integration, see **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)**.

---

## 📜 Available Scripts

| Command | Description |
|---|---|
| `uv run skill-manager` | Launch the application locally |
| `uv run ruff check src tests` | Run linter across the codebase |
| `uv run ruff format src` | Format code automatically |
| `uv run pytest` | Run the unit test suite |
| `uv run pytest --cov=skill_manager` | Run tests with coverage reporting |
| `uv run python scratch/verify_sync.py`| Verify docs match codebase categorization logic |
| `uv run python scripts/build_app.py` | Build the standalone executable locally |
| `uv run semantic-release version` | Manually trigger local version bump (Dry run: `--dry-run`) |

---

## 🚢 Deployment & CI/CD

SkillManager uses a fully automated **Dual-Branch Release Strategy** via GitHub Actions.

### Automated Release Pipeline

The system distinguishes between **Development** and **Stable** releases based on the branch:

1.  **`develop` branch (Pre-releases)**:
    - Every push/merge to `develop` triggers a **Development** release (e.g., `v1.0.0-dev.1`).
    - Use this for testing new features before they are finalized.
2.  **`main` branch (Stable Releases)**:
    - Every push/merge to `main` triggers a **Stable** release (e.g., `v1.0.0`).
    - This is the source for official user-facing downloads.

### Unified Release Process

For both branches, the pipeline performs:
1.  **Versioning**: `python-semantic-release` analyzes commits using Conventional Commits.
2.  **Matrix Build**: Parallel builds for Windows, macOS, and Linux.
3.  **Artifact Verification**: Ensuring all native installers and portable ZIPs are generated successfully.
4.  **Publish**: Attaching platform-specific artifacts (e.g., `SkillManager_Portable_windows.zip`) to the GitHub Release.

### Commit Convention (Strict)

To ensure accurate semantic versioning, all commits MUST follow [Conventional Commits](https://www.conventionalcommits.org/):

| Type | Description | Release Bump |
|---|---|---|
| `feat:` | New feature | Minor |
| `fix:` | Bug fix | Patch |
| `perf:` | Performance improvement | Patch |
| `feat!:` | Breaking change | **Major** |
| `chore:`, `docs:`, `test:` | Maintenance | None |

*Note: The `!` suffix (e.g., `feat!:`) or `BREAKING CHANGE:` in the footer triggers a **Major** version bump automatically.*

---

## 📄 License

MIT License

