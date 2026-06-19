# Release Guide

This document explains the full release lifecycle — from writing a commit to users receiving an update.

---

## Overview

SkillManager uses [python-semantic-release](https://python-semantic-release.readthedocs.io/) with opt-in release tokens. The pipeline is fully automated:

1. You write a commit with an opt-in token (`[patch]`, `[minor]`, `[major]`, `[dev]`)
2. Push to `main` → CI runs → Release workflow triggers
3. python-semantic-release bumps version, creates tag + GitHub Release
4. CI builds Windows artifacts and attaches them to the release
5. TUF publish deploys the update to gh-pages → users auto-update

**Never push a version tag manually.**

---

## How It Works (Step by Step)

### 1. Write a Commit with an Opt-In Token

Every commit to `main` must include exactly one release token in the commit subject:

| Token | Bump | Example |
|---|---|---|
| `[patch]` | Patch (`x.y.z` → `x.y.(z+1)`) | `fix: ui alignment [patch]` |
| `[minor]` | Minor (`x.y.z` → `x.(y+1).0`) | `feat: add new view [minor]` |
| `[major]` | Major (`x.y.z` → `(x+1).0.0`) | `feat!: redesign API [major]` |
| `[dev]` | Pre-release (`x.y.z-dev.N`) | `fix: experimental change [dev]` |

Commits **without** a token are ignored by the release system. This prevents accidental version bumps from `docs:`, `chore:`, `ci:`, etc.

### 2. CI Runs

After you push to `main`, the [CI workflow](../.github/workflows/ci.yml) runs:
1. **Lint** — `ruff check` + `ruff format --check`
2. **Test** — `{windows}` × `{3.12, 3.13}`
3. **Security** — `pip-audit` (non-blocking)
4. **CI Gate** — All checks pass

### 3. Release Workflow Triggers

When CI passes, the [Release workflow](../.github/workflows/release.yml) triggers automatically:

1. **Semantic Release** job:
   - Analyzes commits since the last release
   - Detects opt-in tokens (`[patch]`, `[minor]`, `[major]`, `[dev]`)
   - If `[dev]` is found in the latest commit → creates a pre-release (`x.y.z-dev.N`)
   - Bumps version in `pyproject.toml` and `__init__.py`
   - Generates `CHANGELOG.md`
   - Commits `chore(release): X.Y.Z [skip ci]` to `main`
   - Creates git tag `vX.Y.Z`
   - Creates GitHub Release with auto-generated changelog

2. **Build** job:
   - PyInstaller builds `SkillManager-Setup-{version}.exe` on Windows
   - Artifacts uploaded to GitHub Release

3. **TUF Publish** job:
   - Builds TUF bundle from artifacts
   - Signs and publishes TUF metadata
   - Deploys to `gh-pages` branch

### 4. Users Receive the Update

The installed app polls `gh-pages` for TUF metadata, finds the new version, and auto-updates.

---

## Branch Strategy

| Branch | Purpose | Release Type | Example |
|---|---|---|---|
| `main` | Stable releases | `vX.Y.Z` | Production-ready |
| `main` + `[dev]` token | Pre-releases | `vX.Y.Z-dev.N` | Testing/validation |

---

## CI Pipeline

### PR Checks (`ci.yml`)

Every PR triggers:
1. **Lint** — `ruff check` + `ruff format --check`
2. **Test** — `{windows}` × `{3.12, 3.13}`
3. **Security** — `pip-audit` (non-blocking)
4. **CI Gate** — Aggregation job (required status check)

### Release Pipeline (`release.yml`)

Triggered when CI passes on `main`:
1. **Semantic Release** — Version bump + tag + GitHub Release
2. **Build** — PyInstaller on Windows
3. **Attach** — Artifacts uploaded to GitHub Release
4. **TUF Publish** — Deploy update metadata to gh-pages

---

## Pre-Releases

When you include `[dev]` in a commit subject, the release workflow creates a **pre-release** version:

```
fix: experiment with new UI [dev]
```

This produces: `v2.0.1-dev.1` (pre-release)

Pre-release versions:
- Have lower precedence than stable versions (`2.0.1-dev.1` < `2.0.1`)
- Are marked as pre-release on GitHub
- Are received by users who opted into dev updates
- The pre-release counter increments automatically (`-dev.1`, `-dev.2`, etc.)

---

## Troubleshooting

### Semantic Release didn't create a release

- Check that the commit subject contains `[patch]`, `[minor]`, `[major]`, or `[dev]`
- Check that CI passed before the Release workflow triggered
- Check the [Release workflow logs](https://github.com/dishanagalawatta/SkillManager/actions/workflows/release.yml)

### Build failed

- Check the specific job in the [release workflow](https://github.com/dishanagalawatta/SkillManager/actions/workflows/release.yml)
- Common issues: missing system dependencies, PyInstaller hooks, Inno Setup path

### TUF update not reaching users

- Verify TUF metadata was pushed to `gh-pages`
- Check that TUF signing keys are correctly configured as repository secrets

---

## Required Secrets

| Secret | Purpose | Required |
|---|---|---|
| `GITHUB_TOKEN` | Default token for releases | Yes (auto-provided) |
| `TUF_KEY_ROOT` | TUF root signing key (JSON) | Yes (for TUF publish) |
| `TUF_KEY_SNAPSHOT` | TUF snapshot signing key (JSON) | Yes (for TUF publish) |
| `TUF_KEY_TARGETS` | TUF targets signing key (JSON) | Yes (for TUF publish) |
| `TUF_KEY_TIMESTAMP` | TUF timestamp signing key (JSON) | Yes (for TUF publish) |

---

## Configuration Files

| File | Purpose |
|---|---|
| `pyproject.toml` `[tool.semantic_release]` | python-semantic-release config |
| `src/skill_manager/commit_parser_optin.py` | Custom parser for `[patch]`/`[minor]`/`[major]`/`[dev]` tokens |
| `.github/workflows/release.yml` | Release workflow (semantic-release + build + TUF) |
| `.github/workflows/_build-pyinstaller.yml` | Reusable build job |
| `scripts/publish_tuf_release.py` | TUF publish script |
