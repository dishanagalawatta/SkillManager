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
- **CI/CD**: GitHub Actions with `release-please`
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
# Run all tests in parallel with clean progress (Recommended)
python run_tests.py

# Run with coverage
uv run pytest --cov=skill_manager --cov-report=term-missing

# Run parallel tests with xdist
uv run pytest -n auto --dist loadfile

# Run specific test file
uv run pytest tests/test_parsing.py
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
The GitHub Action `release.yml` automatically builds installers for Windows on version bumps.

### Manual Builds
To build locally for testing:

1. **Run the Packaging Script**:
   ```bash
   uv run python scripts/build_app.py
   ```
   *This script handles icon conversion (png -> ico) and invokes PyInstaller using the spec file.*

2. **Dry-Run**:
   ```bash
   uv run python scripts/build_app.py --dry-run
   ```

3. **Windows Installer**:
   Compile `packaging/windows/installer.iss` using Inno Setup to generate `SkillManager_Setup.exe`.

---

## Release & CI/CD Strategy

SkillManager uses [release-please](https://github.com/googleapis/release-please-action) for automated releases from Conventional Commits. See `docs/CI_CD.md` for the full pipeline architecture and `docs/VERSIONING.md` for versioning rules.

### 1. How Releases Work

1. Push commits to `main` or `develop` following [Conventional Commits](https://www.conventionalcommits.org/)
2. Release-please automatically opens/updates a Release PR
3. Reviewer merges the Release PR → creates a git tag + GitHub Release
4. CI builds artifacts and attaches them to the release

### 2. Branch Strategy

- **`develop` branch**: Development pre-releases (e.g., `v1.5.1-dev.1`)
- **`main` branch**: Stable releases (e.g., `v1.5.0`)

### 3. Commit Convention (Strict)

All commits MUST follow [Conventional Commits](https://www.conventionalcommits.org/):

| Prefix | Type | Release Bump |
|---|---|---|
| `feat:` | New feature | Minor |
| `fix:` | Bug fix | Patch |
| `perf:` | Performance improvement | Patch |
| `feat!:` | Breaking change | Major |
| `chore:`, `docs:`, `test:`, `ci:` | Maintenance | None |

---

## Available Scripts Reference

| Command | Description |
|---|---|
| `uv run skill-manager` | Launch the application |
| `python run_tests.py` | Run unified linting and parallel tests |
| `uv run ruff check src tests` | Run linter only |
| `uv run ruff format src` | Format code |
| `uv run pytest` | Run unit tests |
| `uv run python scripts/build_app.py` | Build executable locally |

