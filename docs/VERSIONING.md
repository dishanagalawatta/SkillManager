# Semantic Versioning Tagging Guide

This document outlines the versioning scheme and release process under the Semantic Versioning (SemVer 2.0.0) standard.

## Core Principle

Versions are bumped **manually** with `scripts/release.py`, which takes an explicit target. Commit messages do not affect versioning: pushing to `main` never bumps the version or creates a tag, and nothing scans for `[patch]`-style tokens. Conventional Commits are still used to keep history readable.

---

## 1. Cutting a Release

Releases are cut manually in two steps: prepare the bump, then tag the merge:

```bash
# 1. Open a release PR carrying the version bump
uv run python scripts/release.py patch   # x.y.z -> x.y.(z+1)
uv run python scripts/release.py minor   # x.y.z -> x.(y+1).0
uv run python scripts/release.py major   # x.y.z -> (x+1).0.0
uv run python scripts/release.py dev     # x.y.z -> x.y.(z+1)-dev.1

# Or set an explicit version (incl. pre-releases)
uv run python scripts/release.py 2.0.1
uv run python scripts/release.py 2.0.1-dev.1

# 2. After the PR merges, tag the merge commit
uv run python scripts/release.py tag
```

### How It Works

1. **Choose the bump**: read `git log` since the last tag and decide — see §2.
2. **Pre-flight**: the script refuses a dirty working tree and runs `ruff` plus `pytest`.
3. **Metadata Synchronization**: `scripts/release.py` automatically synchronizes all 7 metadata files (`pyproject.toml`, `uv.lock` via `uv lock`, `__init__.py`, `installer.iss`, `metainfo.xml`, `README.md`, `CHANGELOG.md`).
4. **Release PR**: the commit is created on `release/vX.Y.Z` and pushed. `main` is protected, so it lands through a pull request that must pass `CI Gate`.
5. **Tag**: after the merge, `scripts/release.py tag` creates the annotated tag `vX.Y.Z` on `main` and pushes it.
6. **Multi-Platform Build**: GitHub Actions builds the multi-platform installer assets (`.deb`, `AppImage`, `.exe`, `SHA256SUMS`) and attaches them to the release.
7. **End-User Distribution**: End users can install or update in one command via `scripts/install.sh`.

---

## 2. Choosing the Bump

| Change | Command | Result |
|---|---|---|
| Bug fix, or a docs/correctness change shipped in a build | `patch` | `x.y.z` → `x.y.(z+1)` |
| New feature, backwards compatible | `minor` | `x.y.z` → `x.(y+1).0` |
| Breaking change | `major` | `x.y.z` → `(x+1).0.0` |
| Trial build before a patch | `dev` | `x.y.z` → `x.y.(z+1)-dev.1` |
| Exact version | `X.Y.Z` / `X.Y.Z-dev.N` | that version |

---

## 3. Version Bump Rules

- **Patch** (`x.y.z` → `x.y.(z+1)`): `patch`
- **Minor** (`x.y.z` → `x.(y+1).0`): `minor`
- **Major** (`x.y.z` → `(x+1).0.0`): `major`
- **Pre-release** (`x.y.(z+1)-dev.N`): `dev`
- The script never picks a bump for you; omitting the target is an error.

---

## 4. Pre-Release Versions

Development pre-releases use the format `x.y.(z+1)-dev.n` (e.g., `2.0.1-dev.1` is
the first pre-release of the upcoming `2.0.1` patch).

### Sequencing

- `dev` on a stable version `x.y.z` → `x.y.(z+1)-dev.1` (first pre-release of the next patch)
- `dev` on a pre-release `x.y.z-dev.n` → `x.y.z-dev.(n+1)` (increments the counter)
- `patch` while on a pre-release `x.y.z-dev.n` → `x.y.z` (promotes the pre-release to stable)
- `minor` / `major` while on a pre-release → drops the suffix (`x.y.z-dev.n` → `x.(y+1).0` / `(x+1).0.0`)

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

Release a breaking change with a `major` bump:

```bash
uv run python scripts/release.py major
```

Say what broke in the commit body and the `CHANGELOG.md` entry, since that is what
users read:

```
feat: redesign configuration API

BREAKING CHANGE: config file format has changed
```

---

## 6. Commit Messages

Commits no longer drive releases — the bump is chosen at release time. Keep them
descriptive anyway: they end up in the release notes.

| Commit | Effect on version |
|---|---|
| `docs: update README` | none |
| `chore: clean up imports` | none |
| `feat: add new view` | none until you run `release.py` |

---

## 7. Sorting and Precedence Rules

Pre-release versions always have *lower* precedence than their standard counterpart:

```
2.0.1-dev.1 < 2.0.1-dev.2 < 2.0.1
```

A `patch` release while a pre-release is active promotes it to stable: if the
latest tag is `2.0.1-dev.3`, running `release.py patch` releases `2.0.1` (not
`2.0.2`).
