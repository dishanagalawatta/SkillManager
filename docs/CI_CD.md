# CI/CD Architecture

## Overview

SkillManager uses GitHub Actions with industry-standard practices: pinned action SHAs, reusable workflows, matrix testing, and release-please for automated releases.

## Workflows

```
.github/workflows/
├── ci.yml                    # PR + main/develop push gate
├── release.yml               # release-please PR-driven releases
└── _reusable/
    ├── setup-python-uv.yml   # Checkout + uv + Python + cache
    ├── lint.yml              # ruff check + format
    ├── test-python.yml       # Matrix test (3 OS × Python version)
    ├── build-pyinstaller.yml # OS-specific PyInstaller build
    └── security-scan.yml     # pip-audit
```

## CI Pipeline (`ci.yml`)

Triggers: push to `main`/`develop`, pull requests, manual dispatch.

```
lint ──────────────────┐
test-py312 (3 OS) ────┤
test-py313 (3 OS) ────┼──► ci-gate (must all pass)
security-scan ────────┘
```

**Concurrency**: PR runs cancel on new push; main/develop runs queue.

## Release Pipeline (`release.yml`)

Uses [release-please](https://github.com/googleapis/release-please-action) for automated releases from conventional commits.

```
Push to main/develop
  └─► release-please opens/updates Release PR
        └─► Reviewer merges Release PR
              └─► Creates tag + GitHub Release
                    └─► build.yml attaches 3-OS artifacts
```

### Commit Convention (Conventional Commits)

| Prefix | Type | Release Bump |
|---|---|---|
| `feat:` | New feature | Minor |
| `fix:` | Bug fix | Patch |
| `feat!:` | Breaking change | Major |
| `perf:` | Performance | Patch |
| `docs:`, `test:`, `chore:`, `ci:` | Maintenance | None |

### Branch Strategy

- **`main`**: Stable releases (`v1.5.0`)
- **`develop`**: Development pre-releases (`v1.5.1-dev.1`)

### Breaking Changes

Add `!` after the type prefix: `feat!: redesign API`

## Action Pinning

All third-party actions are pinned to full commit SHAs (not floating tags). Dependabot automatically proposes weekly updates.

| Action | SHA | Version |
|---|---|---|
| `actions/checkout` | `11bd7190...` | v4.2.2 |
| `actions/setup-python` | `a26af69b...` | v5.6.0 |
| `astral-sh/setup-uv` | `8b06e0d2...` | v6.0.1 |
| `actions/upload-artifact` | `4cec3d8a...` | v4.6.1 |
| `actions/download-artifact` | `d3f86a10...` | v4.3.0 |
| `softprops/action-gh-release` | `da05d552...` | v2.2.2 |

## Branch Protection (Recommended)

Apply via GitHub UI or `gh api`:

- `main`: require CI gate to pass, require 1 approval, no force push
- `develop`: require CI gate to pass, allow force push from bots

## Secret Inventory

| Secret | Purpose | Required |
|---|---|---|
| `GITHUB_TOKEN` | Default token for releases | Yes (auto-provided) |

No external API keys are required for CI. Release-please uses `GITHUB_TOKEN` for PR creation and tagging.

## Local Parity

Run the same checks locally:

```bash
uv run ruff check src tests
uv run ruff format --check src tests
uv run pytest --cov=skill_manager --cov-fail-under=90
```

## Troubleshooting

### Coverage below 90%

Check `tests/test_coverage_boost.py` for uncovered modules. Add targeted tests for the lowest-coverage source files.

### Release-please not creating PR

Ensure commits on `main`/`develop` follow Conventional Commits format. Release-please only creates a PR when there are releasable changes (`feat:`, `fix:`, `perf:`).

### Artifact upload fails

Artifacts are uploaded per-OS. If one OS fails, others still upload. Check the specific build job logs.
