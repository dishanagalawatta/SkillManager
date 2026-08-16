# Development Guide

Welcome to the SkillManager development engine room. This guide covers environment setup, technical workflows, and our automated release pipeline.

---

## Technical Stack

- **Language**: Python 3.12+
- **GUI Framework**: PySide6 (Qt 6.8+) with QML for declarative UI
- **Dependency Management**: [uv](https://astral.sh/uv) (Ultra-fast Python package installer)
- **Linting & Formatting**: `ruff`
- **Packaging**: PyInstaller & Inno Setup
- **Testing**: `pytest` with `pytest-xdist` for parallel execution
- **CI/CD**: GitHub Actions with automated SemVer release pipeline (`scripts/release.py`)
- **Error Tracking**: Sentry
- **Analytics**: PostHog


---

## Local Development

### 1. Prerequisites

- Python 3.12 or higher
- [uv](https://astral.sh/uv)
- Git

### 2. Setup

```bash
git clone https://github.com/dishanagalawatta/SkillManager.git
cd SkillManager
uv sync
```
This automatically creates a `.venv` and installs all dependencies (PySide6, pytest, ruff, etc.).

### 3. Running Locally

Launch the app directly from source:
```bash
uv run skill-manager
# OR
uv run python -m skill_manager
# OR
python run.py
```

---

## Development Workflow

### 1. Code Quality (Linting)
Use **Ruff** for high-performance linting and formatting.

```bash
# Check and fix errors
uv run ruff check src tests --fix

# Format code
uv run ruff format src
```

### 2. Testing
```bash
# Run all checks (lint + format check + parallel tests)
python scripts/dev_test.py

# Run parallel tests with xdist
uv run pytest -n auto --dist loadfile

# Run with coverage
uv run pytest --cov=skill_manager --cov-report=term-missing

# Run specific test file
uv run pytest tests/test_version_sync.py
```

### 3. Manual Smoke Checklist

After dependency or migration work, run the automated checks first, then launch the app and verify:

- Library loads saved sources and discovered skills.
- Search filters skills without UI errors.
- Quick Copy can select skills and copy references.
- Archive and star actions update the list state.
- Copy to project completes for a test project folder.
- Update check handles the latest-release request without blocking the UI.
- Screenshot capture and redaction work correctly.
- Settings persistence (shortcuts, appearance, update preferences).

### 4. Architecture & Documentation Sync

SkillManager maintains a strict parity between the Python categorization logic and the `CATEGORIES.md` guide. If you modify `src/skill_manager/core/parsing/`, ensure `docs/CATEGORIES.md` is updated accordingly.

---

## Building Executables

### Automated Builds
The GitHub Action `release-build.yml` automatically builds installers for Windows and Linux on version tag push (`v*`).

### Manual Builds
To build locally for testing:

1. **PyInstaller Application Build**:
   ```bash
   uv run skill-manager-build
   # Or directly
   python scripts/build_app.py
   ```

2. **Linux Packaging (`.deb` + `AppImage`)**:
   ```bash
   uv run skill-manager-build linux
   # Or directly
   uv run python scripts/build_linux.py --all
   ```

3. **Windows Installer (`SkillManager_Setup.exe`)**:
   ```powershell
   .\packaging\windows\build.ps1 -SkipSign
   ```

---

## Release Strategy

SkillManager uses `scripts/release.py` and GitHub Actions for automated releases. See `docs/RELEASING.md` for the full pipeline architecture and `docs/VERSIONING.md` for versioning rules.

```bash
# Automated SemVer bump and release
uv run python scripts/release.py patch   # x.y.z -> x.y.(z+1)
uv run python scripts/release.py minor   # x.y.z -> x.(y+1).0
uv run python scripts/release.py major   # x.y.z -> (x+1).0.0
```

---

## Available Scripts Reference

| Command | Description |
|---|---|
| `uv run skill-manager` | Launch the desktop application |
| `uv run skill-manager --version` / `-v` | Display application version and exit |
| `python scripts/dev_test.py` | Run unified linting, formatting check, and test suite |
| `uv run ruff check src tests` | Run linter only |
| `uv run ruff format src tests` | Format Python code |
| `uv run pytest -n auto` | Run parallel unit tests |
| `uv run skill-manager-build` | Build PyInstaller bundle |
| `uv run skill-manager-build linux` | Build Linux `.deb` and `AppImage` |
| `uv run python scripts/release.py [bump]` | Synchronize version across repo, tag, and release |
| `bash scripts/install.sh` | 1-command installer/updater for Linux/Ubuntu |


