# Semantic Versioning Tagging Guide

This document outlines the versioning scheme and release process under the Semantic Versioning (SemVer 2.0.0) standard.

## Core Principle

Versions are automatically bumped when pushed to `main` if any commit since the last release tag contains a trigger token (`[patch]`, `[minor]`, `[major]`, `[dev]`) or Conventional Commit prefix (`feat!:`, `feat:`, `fix:`, `perf:`) anywhere in the **commit subject or body**. Commits without a token or prefix are ignored by the release system.

---

## 1. Release Automation

Releases are fully automated via GitHub Actions (`.github/workflows/auto-release.yml`) and can also be run locally via `scripts/release.py`:

```bash
# Auto-detect bump from commit tokens ([patch], [minor], [major])
uv run python scripts/release.py

# Or specify an explicit SemVer bump
uv run python scripts/release.py patch   # x.y.z -> x.y.(z+1)
uv run python scripts/release.py minor   # x.y.z -> x.(y+1).0
uv run python scripts/release.py major   # x.y.z -> (x+1).0.0
```

### How It Works

1. **Commit with Tokens**: Developers annotate commits with tokens like `[patch]`, `[minor]`, or `[major]` (in subject or body).
2. **Automated CI/CD**: On push to `main`, GitHub Actions scans commits since the last tag.
3. **Metadata Synchronization**: `scripts/release.py` automatically synchronizes all 7 metadata files (`pyproject.toml`, `uv.lock` via `uv lock`, `__init__.py`, `installer.iss`, `metainfo.xml`, `README.md`, `CHANGELOG.md`).
4. **Git Tag & Push**: An annotated git tag (`vX.Y.Z`) and release commit (`[skip ci]`) are created and pushed to GitHub.
5. **Multi-Platform Build**: GitHub Actions builds the multi-platform installer assets (`.deb`, `AppImage`, `.exe`, `SHA256SUMS`) and attaches them to the release.
6. **End-User Distribution**: End users can install or update in one command via `scripts/install.sh`.

---

## 2. Release Tokens

Commits can include release tokens in the subject or body:

| Token | Version Bump | Example |
|---|---|---|
| `[patch]` / `fix:` | `x.y.z` → `x.y.(z+1)` | `fix: ui alignment [patch]` |
| `[minor]` / `feat:` | `x.y.z` → `x.(y+1).0` | `feat: add new view [minor]` |
| `[major]` / `feat!:` | `x.y.z` → `(x+1).0.0` | `feat!: redesign API [major]` |
| `[dev]` | `x.y.z` → `x.y.(z+1)-dev.1` | `fix: experiment [dev]` |

---

## 3. Version Bump Rules

- **Patch** (`x.y.z` → `x.y.(z+1)`): `[patch]` token
- **Minor** (`x.y.z` → `x.(y+1).0`): `[minor]` token
- **Major** (`x.y.z` → `(x+1).0.0`): `[major]` token
- **Pre-release** (`x.y.(z+1)-dev.N`): `[dev]` token
- Token precedence in a commit range: `[major]` > `[minor]` > `[dev]` > `[patch]`

---

## 4. Pre-Release Versions

Development pre-releases use the format `x.y.(z+1)-dev.n` (e.g., `2.0.1-dev.1` is
the first pre-release of the upcoming `2.0.1` patch).

### Sequencing

- `[dev]` on a stable version `x.y.z` → `x.y.(z+1)-dev.1` (first pre-release of the next patch)
- `[dev]` on a pre-release `x.y.z-dev.n` → `x.y.z-dev.(n+1)` (increments the counter)
- `[patch]` while on a pre-release `x.y.z-dev.n` → `x.y.z` (promotes the pre-release to stable)
- `[minor]` / `[major]` while on a pre-release → drops the suffix (`x.y.z-dev.n` → `x.(y+1).0` / `(x+1).0.0`)

### Distribution

Pre-releases are tagged `vx.y.z-dev.n` and published as GitHub **prereleases**
(`prerelease: true`). Both the in-app update check and `install.sh --update`
resolve the latest release via the GitHub `/releases/latest` endpoint, which
skips prereleases — so **stable users are never offered dev builds**. Installing
a specific dev build requires the explicit `--version` flag on `install.sh`.

### Precedence

Pre-release versions always have *lower* precedence than their stable counterpart:

```
2.0.1-dev.1 < 2.0.1-dev.2 < 2.0.1
```

---

## 5. Breaking Changes

To signal a major version bump, use the `[major]` token:

```
feat!: redesign configuration API [major]
```

Or:

```
feat: redesign configuration API [major]

BREAKING CHANGE: config file format has changed
```

---

## 6. Commits Without Tokens

Commits that do NOT contain a release token are ignored:

| Commit | Token | Release |
|---|---|---|
| `docs: update README` | None | No release |
| `chore: clean up imports` | None | No release |
| `ci: update workflow` | None | No release |
| `fix: typo in docs [patch]` | `[patch]` | Patch release |
| `feat: new feature [minor]` | `[minor]` | Minor release |

---

## 7. Sorting and Precedence Rules

Pre-release versions always have *lower* precedence than their standard counterpart:

```
2.0.1-dev.1 < 2.0.1-dev.2 < 2.0.1
```

A `[patch]` bump while a pre-release is active promotes it to stable: if the
latest tag is `2.0.1-dev.3`, a `[patch]` commit releases `2.0.1` (not
`2.0.2`).
