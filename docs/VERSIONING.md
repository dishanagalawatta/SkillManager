# Semantic Versioning Tagging Guide

This document outlines the versioning scheme and release process under the Semantic Versioning (SemVer 2.0.0) standard.

## Core Principle

Versions are only bumped when a commit message contains exactly one of the trigger tokens `[patch]`, `[minor]`, `[major]`, or `[dev]`. Commits without a token are ignored by the release system.

---

## 1. Release Automation

Releases are driven by **[python-semantic-release](https://python-semantic-release.readthedocs.io/)** using opt-in release tokens.

### How It Works

1. Push commits to `main` with an opt-in token in the subject
2. CI runs and passes
3. python-semantic-release automatically bumps version, creates tag + GitHub Release
4. CI builds artifacts and attaches them to the release
5. TUF publish deploys the update to gh-pages

---

## 2. Release Tokens

All commits MUST include exactly one release token in the subject:

| Token | Version Bump | Example |
|---|---|---|
| `[patch]` | `x.y.z` → `x.y.(z+1)` | `fix: ui alignment [patch]` |
| `[minor]` | `x.y.z` → `x.(y+1).0` | `feat: add new view [minor]` |
| `[major]` | `x.y.z` → `(x+1).0.0` | `feat!: redesign API [major]` |
| `[dev]` | `x.y.z` → `x.y.z-dev.N` | `fix: experiment [dev]` |

---

## 3. Version Bump Rules

- **Patch** (`x.y.z` → `x.y.(z+1)`): `[patch]` token
- **Minor** (`x.y.z` → `x.(y+1).0`): `[minor]` token
- **Major** (`x.y.z` → `(x+1).0.0`): `[major]` token
- **Pre-release** (`x.y.z-dev.N`): `[dev]` token

---

## 4. Pre-Release Versions

Development pre-releases use the format `x.y.z-dev.n` (e.g., `2.0.1-dev.1`).

- Created when `[dev]` token is found in the latest commit
- The pre-release counter increments automatically
- Pre-release versions have lower precedence than stable versions
- `2.0.1-dev.1` < `2.0.1-dev.2` < `2.0.1`

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
