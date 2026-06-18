# Semantic Versioning Tagging Guide

This document outlines the versioning scheme and release process under the Semantic Versioning (SemVer 2.0.0) standard.

## Core Principle

A pre-release tag always targets the **upcoming** release. For example, `1.5.1-dev.1` signifies the first development build working *towards* the stable `1.5.1` release. It has lower precedence (is mathematically older) than the final `1.5.1` version.

---

## 1. Release Automation

Releases are now driven by **[release-please](https://github.com/googleapis/release-please-action)** using Conventional Commits. There are no manual `[patch]`/`[minor]`/`[major]` triggers in commit messages.

### How It Works

1. Push commits to `main` or `develop` following [Conventional Commits](https://www.conventionalcommits.org/)
2. Release-please automatically opens/updates a Release PR
3. Reviewer merges the Release PR → creates a git tag + GitHub Release
4. CI builds artifacts and attaches them to the release

### Branch Strategy

| Branch | Target Version | Example |
|---|---|---|
| `main` | Stable releases | `v1.5.0` |
| `develop` | Development pre-releases | `v1.5.1-dev.1` |

---

## 2. Commit Convention (Conventional Commits)

All commits MUST follow [Conventional Commits](https://www.conventionalcommits.org/):

| Prefix | Type | Release Bump | Example |
|---|---|---|---|
| `feat:` | New feature | Minor | `feat: add new view` |
| `fix:` | Bug fix | Patch | `fix: ui alignment` |
| `feat!:` | Breaking change | Major | `feat!: redesign API` |
| `perf:` | Performance | Patch | `perf: optimize search` |
| `docs:`, `test:`, `chore:`, `ci:` | Maintenance | None | `docs: update README` |

---

## 3. Version Bump Rules

- **Patch** (`x.y.z` → `x.y.(z+1)`): `fix:`, `perf:`
- **Minor** (`x.y.z` → `x.(y+1).0`): `feat:`
- **Major** (`x.y.z` → `(x+1).0.0`): `feat!:`, `BREAKING CHANGE:`

---

## 4. Pre-Release Versions

Development pre-releases use the format `x.y.z-dev.n` (e.g., `1.5.1-dev.1`). Release-please handles the pre-release counter automatically when merging into `develop`.

---

## 5. Breaking Changes

To signal a major version bump, use the `!` suffix after the type prefix:

```
feat!: redesign configuration API
```

Or include a `BREAKING CHANGE:` footer:

```
feat: redesign configuration API

BREAKING CHANGE: config file format has changed
```

---

## 6. Sorting and Precedence Rules

Pre-release versions always have *lower* precedence than their standard counterpart (`1.5.1-dev.1` < `1.5.1-dev.2` < `1.5.1`). We use the `-dev.n` format for consistent sorting.
