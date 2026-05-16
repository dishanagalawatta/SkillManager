A professional desktop application for managing, syncing, and deploying reusable AI agent skills across multiple project repositories. Built with a **Solid Matte & Liquid Glass** aesthetic, it provides a high-performance, immersive workspace for developers.

---

## ✨ Key Features

- **🚀 Quick Copy Workflow**: Instantly browse project-specific skills and copy formatted references directly to your clipboard using client-specific templates (Antigravity, Gemini CLI, etc.).
- **📚 Centralized Library**: Manage all your markdown-based AI skills in one central location with full-text search and category filtering.
- **🔄 Surgical Sync**: Intelligent synchronization engine that identifies and updates outdated skills across multiple target repositories without full rescans.
- **🎨 Modern UI**: Hardware-accelerated interface built with PySide6/QML, featuring native Windows 11 styling (Mica/Acrylic) and a premium design system.
- **📦 Cross-Platform**: Optimized standalone executables for Windows, macOS, and Linux.

## 🎨 Design System

SkillManager follows the **Solid Matte & Liquid Glass** design guide. It balances the stability of solid, deeply-tinted materials with the depth of frosted glass components.

- **Solid Matte Foundation**: Deeply-tinted material (`#0E1210`) eliminates desktop wallpaper bleed-through.
- **Liquid Glass Pills**: Functional areas are encapsulated in frosted glass containers with 1px reflection borders.
- **Mica/Acrylic Integration**: Native shell effects on Windows for an immersive OS-native feel.

For full details, see **[DESIGN.md](DESIGN.md)**.

- **Language**: Python 3.12+
- **GUI Framework**: PySide6 (Qt 6.8+) with QML
- **Dependency Management**: `uv`
- **Linting & Formatting**: `ruff`
- **Packaging**: PyInstaller & Inno Setup
- **Testing**: `pytest`

## Getting Started (End Users)

If you just want to use the application, head over to the [Releases](https://github.com/yourusername/SkillManager/releases) page and download the installer for your operating system.

- **Windows**: Download and run `SkillManager_Setup.exe`.
- **macOS**: Download and open the `.dmg` file, then drag SkillManager to your Applications folder.
- **Linux**: Download and extract the `.tar.gz` archive.

*Note: Since the executables are not currently code-signed, you may need to click "Run anyway" (Windows SmartScreen) or "Right-click -> Open" (macOS Gatekeeper).*

## Getting Started (Developers)

### 1. Prerequisites
- Python 3.10 or higher
- [uv](https://astral.sh/uv) (Ultra-fast Python package installer)

### 2. Clone the Repository
```bash
git clone https://github.com/yourusername/SkillManager.git
cd SkillManager
```

### 3. Install Dependencies
Using `uv`, sync the environment and dependencies:
```bash
uv sync
```

### 4. Run the Application
Launch the app directly from source:
```bash
uv run skill-manager
# OR
uv run python -m skill_manager
```

SkillManager is built on a **Hub and Spoke** modular architecture to ensure scalability and maintainability:

- **`AppController` (The Hub)**: The main entry point and QML bridge. It coordinates between specialized sub-controllers.
- **Sub-Controllers (`src/skill_manager/controllers/`)**:
    - `UIController`: Manages window geometry, theme state, and asset resolution.
    - `ConfigController`: Handles source/target configuration and `config.json` persistence.
    - `OpsController`: Encapsulates skill operations like copying, deletion, and archiving.
    - `UpdateController`: Orchestrates background synchronization and update state tracking.
- **Core Domain (`src/skill_manager/core/`)**: Pure Python business logic for parsing, discovery, and search indexing.
- **QML Components (`src/skill_manager/SkillManagerComponents/`)**: The declarative UI layer.

For an in-depth look, see **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)**.

| Command | Description |
|---|---|
| `uv run skill-manager` | Launch the application locally |
| `uv run ruff check src` | Run linter across the codebase |
| `uv run pytest` | Run the unit test suite |
| `uv run pytest --cov=skill_manager` | Run tests with coverage reporting |
| `uv run pyinstaller packaging/skill_manager.spec` | Build the standalone executable locally |

## Project Documentation

Detailed documentation can be found in the `docs/` directory:
- [User Guide](docs/USER_GUIDE.md) - How to use the application features.
- [Development Guide](docs/DEVELOPMENT.md) - Detailed local setup and build instructions.
- [Architecture Guide](docs/ARCHITECTURE.md) - System design and packaging architecture.
- [Category Icons](docs/CATEGORY_ICONS.md) - Specification for category-to-emoji mappings and icon sourcing.

## Deployment & CI/CD

SkillManager uses a fully automated GitHub Actions pipeline. Pushing a tag starting with `v` (e.g., `v1.0.0`) triggers the `.github/workflows/release.yml` workflow. This matrix build spins up Windows, macOS, and Linux runners to:
1. Freeze the Python code using `PyInstaller`.
2. Wrap the executables in OS-specific native formats (Inno Setup for Windows, `create-dmg` for macOS).
3. Automatically publish the artifacts to a GitHub Release.

## License

MIT License
