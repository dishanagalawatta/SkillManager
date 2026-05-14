# SkillManager

A professional desktop application for managing, syncing, and deploying reusable AI agent skills across multiple project repositories.

## Key Features

- **Centralized Library**: Manage all your markdown-based AI skills in one central location.
- **Cross-Repository Sync**: Effortlessly copy and update skills between your library and target project directories.
- **Quick Copy Workflow**: Instantly browse project-specific skills and copy formatted references to your clipboard for use in AI prompts.
- **Modern UI**: Sleek, hardware-accelerated interface built with PySide6/QML, featuring a "Solid Matte & Liquid Glass" design system and native window styling (Mica/Acrylic).
- **Cross-Platform**: Standalone executables for Windows, macOS, and Linux.

## Tech Stack

- **Language**: Python 3.10+
- **GUI Framework**: PySide6 (Qt for Python) with QML
- **Dependency Management**: `uv`
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

## Architecture Overview

SkillManager is designed with a strict separation of concerns:
- **`src/skill_manager/core/`**: Contains pure Python business logic, handling file parsing, data modeling (`SkillModel`), updating algorithms, and configuration management.
- **`src/skill_manager/gui/`**: Contains the Python-side UI bridges and styling utilities.
- **`src/skill_manager/SkillManagerComponents/`**: Contains the QML files that define the declarative user interface.
- **`src/skill_manager/app.py`**: The main controller that wires the PySide6 engine to the core data models via Qt Signals and Slots.

For an in-depth look at the architecture, design principles, and packaging pipeline, see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Available Scripts

| Command | Description |
|---|---|
| `uv run skill-manager` | Launch the application locally |
| `uv run pytest` | Run the unit test suite |
| `uv run pytest --cov=skill_manager` | Run tests with coverage reporting |
| `uv run pyinstaller packaging/skill_manager.spec --noconfirm` | Build the standalone executable locally |

## Project Documentation

Detailed documentation can be found in the `docs/` directory:
- [User Guide](docs/USER_GUIDE.md) - How to use the application features.
- [Development Guide](docs/DEVELOPMENT.md) - Detailed local setup and build instructions.
- [Architecture Guide](docs/ARCHITECTURE.md) - System design and packaging architecture.

## Deployment & CI/CD

SkillManager uses a fully automated GitHub Actions pipeline. Pushing a tag starting with `v` (e.g., `v1.0.0`) triggers the `.github/workflows/release.yml` workflow. This matrix build spins up Windows, macOS, and Linux runners to:
1. Freeze the Python code using `PyInstaller`.
2. Wrap the executables in OS-specific native formats (Inno Setup for Windows, `create-dmg` for macOS).
3. Automatically publish the artifacts to a GitHub Release.

## License

MIT License
