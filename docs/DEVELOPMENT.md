# Development Guide

This guide covers how to set up the SkillManager development environment, run tests, and build the application locally.

## Prerequisites

- **Python 3.12+**
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
```

## Development Workflow

### 1. Code Quality (Linting)
SkillManager uses **Ruff** for high-performance linting and formatting. It is configured via `ruff.toml`.

```bash
# Check for linting errors
uv run ruff check src tests

# Automatically fix fixable errors
uv run ruff check src tests --fix

# Format the code
uv run ruff format src
```

### 2. Testing
SkillManager uses `pytest` for unit testing.

```bash
# Run all tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=skill_manager

# Run specific tests
uv run pytest tests/test_parsing.py
```

### 3. CI/CD Standards
All code changes must pass the following criteria:
1. **Lint-Clean**: `uv run ruff check src tests` must return no errors.
2. **Type-Safe**: Use Python type hints in all new code.
3. **Tested**: New features should include unit tests in the `tests/` directory.
4. **Coverage-Aware**: Run `uv run pytest --cov=skill_manager --cov-report=term-missing` before larger changes.

### 4. Documentation Synchronization
SkillManager maintains a strict 1:1 mapping between the Python categorization logic and the `CATEGORIES.md` guide. 

If you add or modify categories in `src/skill_manager/core/parsing.py` or `src/skill_manager/app.py`, you must run the verification script to ensure documentation parity:

```bash
# Verify that documentation matches the current codebase logic
uv run python scratch/verify_sync.py
```

This script extracts keywords and emoji mappings directly from the source code and highlights any discrepancies in the documentation.

## Building Executables

SkillManager is packaged into standalone executables using PyInstaller.

### Automated Builds (Recommended)
The quality pipeline in `.github/workflows/quality.yml` runs linting and tests on pushes and pull requests. The release pipeline in `.github/workflows/release.yml` builds installers for Windows, macOS, and Linux when a new `v*` tag is pushed to GitHub.

### Manual Builds

If you need to build the executable locally for testing:

1. **Prerequisites & Virtual Environment**:
   Verify that all packaging and imaging dependencies (`pyinstaller` and `pillow`) are synced inside your local environment:
   ```bash
   uv sync
   ```

2. **Run the Packaging Script**:
   Instead of calling raw `pyinstaller` commands, use the unified Python build script. This script automatically handles preparing multi-size icons for the desktop executable and running PyInstaller with the spec configuration:
   ```bash
   uv run python scripts/build_app.py
   ```

3. **Dry-Run Testing**:
   You can verify that the asset pre-processing pipeline (e.g. converting `logo.png` to a multi-size Windows icon file `logo.ico` supporting resolutions from 16x16 to 256x256) operates correctly without running the long compiling phase:
   ```bash
   uv run python scripts/build_app.py --dry-run
   ```

4. **Inno Setup (Windows Installer)**:
   The Windows installer script (`packaging/windows/installer.iss`) is fully bound to the generated `assets/brand/logo.ico`. Once the local PyInstaller build finishes, compile the Inno Setup script using the Inno Setup Compiler (`ISCC.exe`) to generate the `SkillManager_Setup.exe` installer.

| Command | Description |
|---|---|
| `uv run skill-manager` | Launch the application locally |
| `uv run ruff check src tests` | Run ruff linter |
| `uv run ruff format src` | Format code with ruff |
| `uv run pytest` | Run the unit test suite |
| `uv run python scripts/build_app.py` | Automate icon conversion and compile executable |
| `uv run python scripts/build_app.py --dry-run` | Dry-run validation of the build environment |

## Release Process

SkillManager uses **python-semantic-release** to automate versioning and releases.

### 1. Automated Releases (CI)
On every push or merge to the `main` branch, a unified GitHub Action (`release.yml`):
- **Stage 1**: Analyzes commit messages using Conventional Commits and handles versioning/tagging via `python-semantic-release`.
- **Stage 2**: Triggers a parallel matrix build across Windows, macOS, and Linux to generate installers and portable archives.
- **Stage 3**: Collects all artifacts and attaches them to the GitHub **Pre-release**.

### 2. Manual Release Trigger
You can manually trigger a release by running `python-semantic-release` locally:

```bash
# Install tool and dependencies
uv sync

# Dry-run to see what would happen (calculates next version)
uv run semantic-release version --print

# Perform local version bump and tag (updates files and creates git tag)
uv run semantic-release version --no-push
```

### 3. Commit Guidelines (Conventional Commits)
We strictly follow [Conventional Commits](https://www.conventionalcommits.org/). The commit message prefix determines the next version bump:

| Prefix | Type of Change | Release Bump |
|---|---|---|
| `feat:` | A new feature | Minor |
| `fix:` | A bug fix | Patch |
| `perf:` | A code change that improves performance | Patch |
| `refactor:` | A code change that neither fixes a bug nor adds a feature | None |
| `style:` | Changes that do not affect the meaning of the code | None |
| `docs:` | Documentation only changes | None |
| `test:` | Adding missing tests or correcting existing tests | None |
| `chore:` | Changes to the build process or auxiliary tools | None |

*Important: To trigger a **Major** release, append `!` to the prefix (e.g., `feat!:`) or include `BREAKING CHANGE:` in the commit footer.*
