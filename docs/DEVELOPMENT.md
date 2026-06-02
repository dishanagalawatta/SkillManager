# 🛠️ Development Guide

Welcome to the SkillManager development engine room. This guide covers environment setup, technical workflows, and our automated release pipeline.

---

## 🏗️ Technical Stack

- **Language**: Python 3.12+
- **GUI Framework**: PySide6 (Qt 6.8+) with QML for declarative UI
- **Dependency Management**: [uv](https://astral.sh/uv) (Ultra-fast Python package installer)
- **Linting & Formatting**: `ruff`
- **Packaging**: PyInstaller & Inno Setup
- **Testing**: `pytest`
- **CI/CD**: GitHub Actions with `python-semantic-release`

---

## 🚀 Local Development

### 1. Prerequisites

- Python 3.12 or higher
- [uv](https://astral.sh/uv)
- Git

### 2. Setup

```bash
git clone https://github.com/yourusername/SkillManager.git
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
```

---

## 🛠️ Development Workflow

### 1. Code Quality (Linting)
We use **Ruff** for high-performance linting and formatting.

```bash
# Check and fix errors
uv run ruff check src tests --fix

# Format code
uv run ruff format src
```

### 2. Testing
```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=skill_manager --cov-report=term-missing
```

### 3. Manual Smoke Checklist

After dependency or migration work, run the automated checks first, then launch the app and verify:

- Library loads saved sources and discovered skills.
- Search filters skills without UI errors.
- Quick Copy can select skills and copy references.
- Archive and star actions update the list state.
- Copy to project completes for a test project folder.
- Update check handles the latest-release request without blocking the UI.

### 4. Architecture & Documentation Sync
SkillManager maintains a strict parity between the Python categorization logic and the `CATEGORIES.md` guide. If you modify `src/skill_manager/core/parsing.py`, run:

```bash
uv run python scratch/verify_sync.py
```

---

## 📦 Building Executables

### Automated Builds
The GitHub Action `release.yml` automatically builds installers for Windows, macOS, and Linux on version bumps.

### Manual Builds
To build locally for testing:

1. **Run the Packaging Script**:
   ```bash
   uv run python scripts/build_app.py
   ```
   *Note: This script handles icon conversion (png -> ico) and invokes PyInstaller using the spec file.*

2. **Dry-Run**:
   ```bash
   uv run python scripts/build_app.py --dry-run
   ```

3. **Windows Installer**:
   Compile `packaging/windows/installer.iss` using Inno Setup to generate `SkillManager_Setup.exe`.

---

## 🚢 Release & CI/CD Strategy

SkillManager uses a strictly **Opt-in Release Strategy**. Versions are only bumped when explicit trigger words are included in the commit message.

### 1. Release Triggers

| Trigger | Release Type | Example |
|---|---|---|
| **`[major]`** | Stable Major Bump | `feat: final release [major]` |
| **`[minor]`** | Stable Minor Bump | `feat: add new view [minor]` |
| **`[patch]`** | Stable Patch Bump | `fix: ui alignment [patch]` |
| **`[dev]`** | Development Release | `feat: experimental icons [dev]` |

### 2. Branch Strategy

- **`develop` branch**: Merges with any trigger create a **Development** pre-release (e.g., `v1.0.0-dev.1`).
- **`main` branch**: Merges with `[major/minor/patch]` create a **Stable** release (e.g., `v1.0.0`).

### 3. Commit Convention (Strict)

All commits MUST follow [Conventional Commits](https://www.conventionalcommits.org/):

| Prefix | Type | Release Bump |
|---|---|---|
| `feat:` | New feature | Minor |
| `fix:` | Bug fix | Patch |
| `perf:` | Performance improvement | Patch |
| `feat!:` | Breaking change | **Major** |
| `chore:`, `docs:`, `test:` | Maintenance | None |

---

## 📜 Available Scripts Reference

| Command | Description |
|---|---|
| `uv run skill-manager` | Launch the application |
| `uv run ruff check src tests`| Run linter |
| `uv run pytest` | Run unit tests |
| `uv run python scripts/build_app.py` | Build executable locally |
| `uv run semantic-release version` | Dry-run version bump |
