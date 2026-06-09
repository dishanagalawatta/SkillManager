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
- **CI/CD**: GitHub Actions with `python-semantic-release`
- **Error Tracking**: Sentry
- **Analytics**: PostHog
- **Secure Updates**: TUF (The Update Framework)

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
The GitHub Action `release.yml` automatically builds installers for Windows, macOS, and Linux on version bumps.

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

### Auto-Update Releases (Tufup)
We use `tufup` (The Update Framework) for secure background updates.

1. **Initialize Repository** (First time only):
   ```bash
   uv run python scripts/publish_tuf_release.py --version 1.0.0 --bundle dist/SkillManager --init
   ```
   **CRITICAL SECURITY:** This generates private keys in `tuf_keys/`.
   - **DO NOT** commit these keys to Git (they are ignored by `.gitignore`).
   - **BACKUP** this folder to a secure location. If lost, you cannot update your users.

2. **Publish a New Version**:
   ```bash
   uv run python scripts/publish_tuf_release.py --version 1.0.1 --bundle dist/SkillManager
   ```

3. **Deploy to GitHub Pages**:
   - Updates are served via the `gh-pages` branch.
   - Push `tuf_repo/metadata` to `gh-pages:/metadata/`.
   - Push `tuf_repo/targets` to `gh-pages:/targets/`.

---

## Release & CI/CD Strategy

SkillManager uses a strictly **Opt-in Release Strategy**. Versions are only bumped when explicit trigger words are included in the commit message.

### 1. Release Triggers

| Trigger | Release Type | Example |
|---|---|---|
| `[major]` | Stable Major Bump | `feat: final release [major]` |
| `[minor]` | Stable Minor Bump | `feat: add new view [minor]` |
| `[patch]` | Stable Patch Bump | `fix: ui alignment [patch]` |
| `[dev]` | Development Release | `feat: experimental icons [dev]` |
| `[preminor]` | Pivot to Minor Pre-release | `feat: scope change [preminor]` |
| `[premajor]` | Pivot to Major Pre-release | `feat: breaking change [premajor]` |

### 2. Branch Strategy

- **`develop` branch**: Merges with any trigger create a Development pre-release (e.g., `v1.0.0-dev.1`).
- **`main` branch**: Merges with `[major/minor/patch]` create a Stable release (e.g., `v1.0.0`).

### 3. Version Bump Logic

The `scripts/version_bump_calculator.py` script handles edge cases:
- **Cross-grade detection**: Prevents graduating minor/major prerelease via `[patch]`.
- **Dev cycle continuation**: `[dev]` from dev state increments prerelease counter.
- **Dev cycle start**: `[dev]` from stable state initializes a new dev cycle.
- **Scope pivot**: `[preminor]`/`[premajor]` from dev state pivots the target version.

### 4. Commit Convention (Strict)

All commits MUST follow [Conventional Commits](https://www.conventionalcommits.org/):

| Prefix | Type | Release Bump |
|---|---|---|
| `feat:` | New feature | Minor |
| `fix:` | Bug fix | Patch |
| `perf:` | Performance improvement | Patch |
| `feat!:` | Breaking change | Major |
| `chore:`, `docs:`, `test:` | Maintenance | None |

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
| `uv run python scripts/publish_tuf_release.py` | Publish TUF update |
| `uv run python scripts/version_bump_calculator.py` | Test version bump logic |
