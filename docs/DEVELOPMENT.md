# Development Guide

This guide covers how to set up the SkillManager development environment, run tests, and build the application locally.

## Prerequisites

- **Python 3.10+** (Python 3.14 recommended for latest performance)
- **uv**: The ultra-fast Python package installer and resolver.
  - Install via PowerShell: `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`
  - Install via Homebrew: `brew install uv`
- **Git**

## Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/SkillManager.git
   cd SkillManager
   ```

2. **Sync dependencies using uv:**
   ```bash
   uv sync
   ```
   This will automatically create a `.venv` directory and install all required dependencies (including PySide6) and development dependencies (pytest, etc.) defined in `pyproject.toml`.

## Running the Application Locally

You can run the application directly from the source code without compiling it:

```bash
uv run skill-manager
# OR
uv run python -m skill_manager
```

## Running Tests

SkillManager uses `pytest` for unit testing.

```bash
# Run all tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=skill_manager

# Run specific tests
uv run pytest tests/test_parsing.py
```

## Building Executables

SkillManager is packaged into standalone executables using PyInstaller.

### Automated Builds (Recommended)
The CI/CD pipeline in `.github/workflows/release.yml` automatically handles building installers for Windows, macOS, and Linux when a new `v*` tag is pushed to GitHub.

### Manual Builds

If you need to build the executable locally for testing:

1.  **Ensure PyInstaller is installed:**
    It should be installed via `uv sync`, but if not:
    ```bash
    uv pip install pyinstaller pillow
    ```

2.  **Run PyInstaller:**
    ```bash
    uv run pyinstaller packaging/skill_manager.spec --noconfirm
    ```

3.  **Locate Output:**
    The standalone executable and its bundled dependencies will be located in the `dist/SkillManager/` directory.

### Windows Native Installer (Inno Setup)
If you have Inno Setup installed on Windows, you can compile the `packaging/windows/installer.iss` file to generate the final `SkillManager_Setup.exe`.
