# CI/CD Architecture

## Overview

SkillManager uses GitHub Actions with industry-standard practices: pinned action SHAs, reusable workflows, and python-semantic-release with opt-in tokens for automated releases.

## Workflows

```
.github/workflows/
├── ci.yml                    # PR + main/develop push gate
├── release.yml               # semantic-release + build + attach assets
├── _lint.yml                 # Ruff check + format (reusable)
├── _test-python.yml          # Test on Windows (reusable)
├── _build-pyinstaller.yml    # PyInstaller build for Windows (reusable)
└── _security-scan.yml        # pip-audit (reusable)
```

## CI Pipeline (`ci.yml`)

Triggers: push to `main`/`develop`, pull requests, manual dispatch.

```
lint ──────────────────┐
test-py312 (Windows) ──┤
test-py313 (Windows) ──┼──► ci-gate (must all pass)
security-scan ────────┘
```

**Concurrency**: PR runs cancel on new push; main/develop runs queue.

## Release Pipeline (`release.yml`)

Uses [python-semantic-release](https://python-semantic-release.readthedocs.io/) with opt-in tokens for automated releases.

```
Push to main (with [patch]/[minor]/[major]/[dev] token)
  └─► CI workflow runs (lint, tests, security, gate)
        └─► Release workflow triggers on CI completion
              └─► Semantic Release (version bump + tag + GitHub Release)
                    └─► Build (PyInstaller on Windows)
                          └─► Attach Assets (upload to GitHub Release)
                                └─► Users download from GitHub Releases
```

The Release workflow is gated on CI success via `workflow_run` trigger.

### Opt-In Release Tokens

| Token | Version Bump | Example |
|---|---|---|
| `[patch]` | Patch (`x.y.z` → `x.y.(z+1)`) | `fix: ui alignment [patch]` |
| `[minor]` | Minor (`x.y.z` → `x.(y+1).0`) | `feat: add new view [minor]` |
| `[major]` | Major (`x.y.z` → `(x+1).0.0`) | `feat!: redesign API [major]` |
| `[dev]` | Pre-release (`x.y.z-dev.N`) | `fix: experiment [dev]` |

Commits without a token are ignored by the release system.

### Branch Strategy

- **`main`**: Stable releases (`vX.Y.Z`) or pre-releases with `[dev]` token

### Breaking Changes

Use the `[major]` token: `feat!: redesign API [major]`

## Action Pinning

All third-party actions are pinned to full commit SHAs (not floating tags). Dependabot automatically proposes weekly updates.

| Action | SHA | Version |
|---|---|---|
| `actions/checkout` | `11bd7190...` | v4.2.2 |
| `actions/setup-python` | `a26af69b...` | v5.6.0 |
| `astral-sh/setup-uv` | `6b9c6063...` | v6.0.1 |
| `actions/upload-artifact` | `4cec3d8a...` | v4.6.1 |
| `actions/download-artifact` | `d3f86a10...` | v4.3.0 |
| `softprops/action-gh-release` | `da05d552...` | v2.2.2 |
| `peaceiris/actions-gh-pages` | `4f9cc660...` | v4.0.0 |
| `python-semantic-release/python-semantic-release` | — | v10.5.3 |

## Branch Protection (Recommended)

Apply via GitHub UI or `gh api`:

- `main`: require CI gate to pass, require 1 approval, no force push

## Secret Inventory

| Secret | Purpose | Required |
|---|---|---|
| `GITHUB_TOKEN` | Default token for releases | Yes (auto-provided) |

### Suppressed CVEs

See [docs/SECURITY.md](SECURITY.md) for the list of CVEs silenced in
`pip-audit --ignore-vuln` and the threat-model rationale.

## Local Parity

Run the same checks locally:

```bash
uv run ruff check src tests
uv run ruff format --check src tests
uv run pytest --cov=skill_manager --cov-fail-under=90
```

## Required Repo Settings

The Release workflow depends on the following repo-level setting (Settings → Actions → General → Workflow permissions):

- **Workflow permissions**: "Read and write permissions"
- **Allow GitHub Actions to create and approve pull requests**: enabled

## Troubleshooting

### Coverage below 90%

Check `tests/test_coverage_boost.py` for uncovered modules. Add targeted tests for the lowest-coverage source files.

### Semantic Release not creating release

Ensure commits on `main` include an opt-in token (`[patch]`, `[minor]`, `[major]`, or `[dev]`) in the subject line.

### Artifact upload fails

Check the specific build job logs in the [release workflow](https://github.com/dishanagalawatta/SkillManager/actions/workflows/release.yml).
