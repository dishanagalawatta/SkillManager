# CI/CD Architecture

## Overview

SkillManager uses GitHub Actions with industry-standard practices: pinned action SHAs, reusable workflows, and automated release builds triggering on tag pushes.

## Workflows

```
.github/workflows/
├── ci.yml                    # PR + main push gate (lint + test + security)
├── auto-release.yml          # Automated version bump and git tagging on main push
├── release-build.yml         # Multi-platform packaging (Windows .exe + Linux .deb & AppImage)
├── _lint.yml                 # Ruff check + format (reusable)
├── _test-python.yml          # Test suite runner (reusable)
├── _build-pyinstaller.yml    # PyInstaller build for Windows (reusable)
└── _security-scan.yml        # pip-audit (reusable)
```

## CI Pipeline (`ci.yml`)

Triggers: push to `main`, pull requests, manual dispatch.

```mermaid
flowchart LR
    A[PR / Push to main] --> B[Lint: ruff]
    A --> C["Test: Python 3.12 (windows-latest)"]
    A --> D["Test: Python 3.13 (windows-latest)"]
    B --> E[CI Gate: all checks pass]
    C --> E
    D --> E
```

**Concurrency**: PR runs cancel on new push; main runs queue.

---

## Automated Versioning & Release Pipeline (`auto-release.yml` & `release-build.yml`)

Releases are fully automated from Git commits and tags:

```mermaid
flowchart TD
    subgraph "1. Developer Push"
        A["git push origin main (with [patch], [minor], [major], or feat:/fix:)"]
    end

    subgraph "2. Auto Version Bump & Tagging (auto-release.yml)"
        A --> B["auto-release.yml triggers on main"]
        B --> C["Scan commit subject & body for SemVer tokens"]
        C --> D["uv run python scripts/release.py auto --only-if-triggered"]
        D --> E["Sync version in 6 metadata files & commit [skip ci]"]
        E --> F["Create annotated git tag: vX.Y.Z"]
        F --> G["Push commit & tag to origin main"]
    end

    subgraph "3. Multi-Platform Build & Publish (release-build.yml)"
        G --> H["release-build.yml triggers on tag v*"]
        H --> I["Build Windows installer: SkillManager_Setup.exe"]
        H --> J["Build Linux .deb & AppImage"]
        I --> K["Compute SHA256 checksums: SHA256SUMS"]
        J --> K
        K --> L["Publish GitHub Release with all binary assets"]
        L --> M["End users install/update via 1-command installer script"]
    end
```

The Release workflow compiles all platform binaries on native GitHub runners, signs Windows installers (when certificate secrets are present), and attaches verified artifacts to the GitHub Release.

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

---

## Dual-Workflow Architecture on `main` Push

When a push to `main` occurs, GitHub Actions triggers two distinct workflows in parallel:

```mermaid
flowchart TD
    A["git push origin main"] --> B["CI (ci.yml)\n• Read-only permissions\n• Ruff lint + format check\n• Python 3.12 & 3.13 test matrix\n• Quality Gate"]
    A --> C["Auto Version & Release (auto-release.yml)\n• Write permissions\n• Scans commits for SemVer tokens\n• Tags vX.Y.Z & triggers release-build.yml\n• Exits in ~5s if no bump needed"]
```

### Why They Are Decoupled
1. **Security Isolation (Least Privilege)**: `CI` runs on untrusted Pull Requests with strictly read-only repository permissions (`contents: read`). `Auto Version & Release` requires write permissions (`contents: write`, `actions: write`) to push tags and dispatch workflows, and is locked to `main`.
2. **Speed & Efficiency**: `auto-release.yml` performs an instantaneous pre-flight check via `scripts/release.py auto --only-if-triggered`. If no SemVer tokens are found, it terminates in ~5 seconds without consuming heavy runner minutes.
3. **Pull Request Support**: `ci.yml` validates PRs to prevent broken code from landing on `main`, while release automation only acts once changes are merged to `main`.

### `paths-ignore` & Lockfile Behavior
Both `ci.yml` and `auto-release.yml` ignore changes restricted strictly to documentation and reference directories:
```yaml
paths-ignore:
  - 'docs/**'
  - '*.md'
  - 'assets/**'
  - '.agents/**'
  - 'image/**'
  - 'conductor/**'
  - 'LICENSE'
```
- **Doc-only commits** (`docs/`, `README.md`, etc.) are skipped automatically by GitHub Actions.
- **Dependency & lockfile updates** ([`uv.lock`](file:///home/dikka/Documents/01-Projects/27-SkillManager/skill-manager/uv.lock)) or code changes are **not** ignored, triggering both workflows to ensure all tests pass and any release tokens are processed.

---

## Branch Protection (Recommended)

Apply via GitHub UI or `gh api`:

- `main`: require CI gate to pass, require 1 approval, no force push

## Secret Inventory

| Secret | Purpose | Required |
|---|---|---|
| `GITHUB_TOKEN` | Default token for releases | Yes (auto-provided) |
| `WIN_PFX_B64` | Base64-encoded Windows code signing certificate | Optional |
| `WIN_PFX_PASS` | Password for Windows code signing certificate | Optional |

### Suppressed CVEs

See [docs/SECURITY.md](SECURITY.md) for the list of CVEs silenced in
`pip-audit --ignore-vuln` and the threat-model rationale.

## Local Parity

Run the same checks locally:

```bash
export QML_DISABLE_DISK_CACHE=1  # ADR-0001 — prevents stale QML bytecode
uv run ruff check src tests
uv run ruff format --check src tests
uv run pytest --cov=skill_manager --cov-fail-under=80
```

## Required Repo Settings

The Release workflow depends on the following repo-level setting (Settings → Actions → General → Workflow permissions):

- **Workflow permissions**: "Read and write permissions"
- **Allow GitHub Actions to create and approve pull requests**: enabled

## Troubleshooting

### Coverage below threshold
Check `tests/test_coverage_boost.py` for uncovered modules. Add targeted tests for the lowest-coverage source files.

### Auto Release not creating release
Ensure commits on `main` include an opt-in SemVer token (`[patch]`, `[minor]`, `[major]`, or `[dev]`) or Conventional Commit prefix (`feat!:`, `feat:`, `fix:`, `perf:`) in the commit subject or body.

### Artifact upload fails
Check the specific build job logs in the [release workflow](https://github.com/dishanagalawatta/SkillManager/actions/workflows/release-build.yml).
