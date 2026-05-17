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

1.  **Ensure PyInstaller is installed:**
    It should be installed via `uv sync`, but if not:
    ```bash
    uv pip install pyinstaller pillow
    ```

| Command | Description |
|---|---|
| `uv run skill-manager` | Launch the application locally |
| `uv run ruff check src tests` | Run ruff linter |
| `uv run ruff format src` | Format code with ruff |
| `uv run pytest` | Run the unit test suite |
| `uv run pyinstaller packaging/skill_manager.spec` | Build the standalone executable |
