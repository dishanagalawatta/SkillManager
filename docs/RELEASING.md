# Release Guide

This document explains the full release lifecycle — from writing a commit to users receiving an update.

---

## Overview

SkillManager uses [release-please](https://github.com/googleapis/release-please-action) to automate releases. The pipeline is fully automated:

1. You write a commit following [Conventional Commits](https://www.conventionalcommits.org/)
2. Release-please opens/updates a Release PR
3. A maintainer merges the Release PR → creates a git tag + GitHub Release
4. CI builds 3-OS artifacts and attaches them to the release
5. Users receive the update via TUF (manual post-release step)

**Never push a version tag manually.**

---

## How It Works (Step by Step)

### 1. Write Conventional Commits

Every commit to `main` or `develop` must follow [Conventional Commits](https://www.conventionalcommits.org/):

| Prefix | Type | Bump | Example |
|---|---|---|---|
| `feat:` | New feature | Minor | `feat: add new view` |
| `fix:` | Bug fix | Patch | `fix: ui alignment` |
| `perf:` | Performance | Patch | `perf: optimize search` |
| `feat!:` | Breaking change | Major | `feat!: redesign API` |
| `docs:`, `test:`, `chore:`, `ci:` | Maintenance | None | `docs: update README` |

### 2. Release-please Creates a Release PR

After you push to `main`, release-please automatically:
- Analyzes your commits since the last release
- Determines the next version based on commit types
- Opens (or updates) a Release PR with:
  - Updated version in `pyproject.toml` and `__init__.py`
  - Auto-generated `CHANGELOG.md` entries
  - A new git tag reference

The Release PR is titled: `chore: release v<version>`

### 3. Merge the Release PR

When a maintainer merges the Release PR:
- A git tag `v<version>` is created
- A GitHub Release is published with the auto-generated changelog
- The CI build pipeline is triggered

### 4. CI Builds Artifacts

The [release workflow](../.github/workflows/release.yml) runs the [build job](../.github/workflows/_reusable/build-pyinstaller.yml) on 3 OS:

| OS | Artifact | Built By |
|---|---|---|
| Windows | `SkillManager-Setup-{version}.exe` | Inno Setup |
| macOS | `SkillManager-macOS-{version}.zip` | PyInstaller |
| Linux | `SkillManager-Linux-{version}.zip` | PyInstaller |

Artifacts are automatically attached to the GitHub Release.

### 5. Publish TUF Update (Manual)

After the release is published, you must manually publish the TUF update so users receive it via the auto-update mechanism:

```bash
# Build the update bundle
uv run python scripts/build_app.py

# Publish to TUF repository
uv run python scripts/publish_tuf_release.py --version <version> --bundle dist/SkillManager

# Deploy to GitHub Pages
# (push tuf_repo/metadata and tuf_repo/targets to gh-pages branch)
```

See [DEVELOPMENT.md](DEVELOPMENT.md#auto-update-releases-tufup) for detailed instructions.

---

## Branch Strategy

| Branch | Purpose | Release Type | Example |
|---|---|---|---|
| `main` | Stable releases | `v1.5.0` | Production-ready |
| `develop` | Pre-releases | `v1.5.1-dev.1` | Testing/validation |

---

## CI Pipeline

### PR Checks (`ci.yml`)

Every PR triggers:
1. **Lint** — `ruff check` + `ruff format --check`
2. **Test** — Matrix: `{ubuntu, macos, windows}` × `{3.12, 3.13}`
3. **Security** — `pip-audit` (non-blocking)
4. **CI Gate** — Aggregation job (required status check)

### Release Pipeline (`release.yml`)

Triggered by merging a Release PR:
1. **Build** — PyInstaller on 3 OS
2. **Attach** — Artifacts uploaded to GitHub Release

---

## Troubleshooting

### Release-please didn't create a Release PR

- Check that commits follow Conventional Commits format
- Check the [release-please-action logs](https://github.com/dishanagalawatta/SkillManager/actions/workflows/release.yml)
- Verify `.github/release-please-config.json` is correct

### Build failed on one OS

- Check the specific job in the [release workflow](https://github.com/dishanagalawatta/SkillManager/actions/workflows/release.yml)
- Common issues: missing system dependencies, PyInstaller hooks, Inno Setup path

### TUF update not reaching users

- Verify `tuf_repo/metadata` and `tuf_repo/targets` are pushed to `gh-pages`
- Check that the version in `.release-please-manifest.json` matches the release

---

## Configuration Files

| File | Purpose |
|---|---|
| `.github/release-please-config.json` | Package config, changelog sections, extra files |
| `.github/.release-please-manifest.json` | Current version tracking |
| `.github/workflows/release.yml` | Release workflow (release-please + build) |
| `.github/workflows/_reusable/build-pyinstaller.yml` | Reusable build job |
| `scripts/build_app.py` | PyInstaller build script |
| `scripts/publish_tuf_release.py` | TUF publish script |
