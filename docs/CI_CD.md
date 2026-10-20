# CI/CD Architecture

## Overview

SkillManager uses GitHub Actions with industry-standard practices: pinned action SHAs, reusable workflows, and automated release builds triggering on tag pushes.

## Workflows

```
.github/workflows/
├── ci.yml                    # PR + main push gate (lint + test + security)
├── release-build.yml         # Multi-platform packaging (Windows .exe + Linux .deb & AppImage)
├── _lint.yml                 # Ruff check + format (reusable)
├── _test-python.yml          # Test suite runner (reusable)
├── _build-pyinstaller.yml    # PyInstaller build for Windows (reusable)
└── _security-scan.yml        # pip-audit (reusable)
```

## CI Pipeline (`ci.yml`)

Triggers: push to `main` (which only happens through a merged pull request),
every pull request, and manual dispatch.

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

## Release Pipeline (`release-build.yml`)

Releases are triggered by a tag you push yourself with `scripts/release.py` — no
workflow bumps the version. `main` is protected, so the bump lands through a pull
request and the tag is pushed on the merge commit:

```mermaid
flowchart TD
    subgraph "1. Release PR"
        A["uv run python scripts/release.py <bump>"] --> B["Pre-flight: ruff + pytest"]
        B --> C["Sync version in 7 metadata files on release/vX.Y.Z"]
        C --> D["Push branch & open pull request"]
        D --> E["CI Gate green, then merge"]
    end

    subgraph "2. Tag & Build (release-build.yml)"
        E --> F["uv run python scripts/release.py tag"]
        F --> G["git push origin vX.Y.Z"]
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

Dev pre-releases (`vX.Y.Z-dev.N` tags) are published with `prerelease: true` and are skipped by the GitHub `/releases/latest` endpoint, so stable users never receive them via `install.sh --update` or the in-app update check. Running `release.py patch` while a dev line is active promotes it to stable. See [VERSIONING.md §4](VERSIONING.md#4-pre-release-versions).

## Action Pinning

All third-party actions are pinned to full commit SHAs (not floating tags). Dependabot automatically proposes weekly updates.

| Action | SHA | Version |
|---|---|---|
| `actions/checkout` | `3d3c42e5...` | v7.0.1 |
| `actions/setup-python` | `5fda3b95...` | v7.0.0 |
| `astral-sh/setup-uv` | `c18668ad...` | v10.2.0 |
| `actions/upload-artifact` | `043fb46d...` | v7.0.1 |
| `actions/download-artifact` | `3e5f45b2...` | v8 |
| `softprops/action-gh-release` | `efb35369...` | v3 |
| `zizmorcore/zizmor-action` | `cc914d7f...` | v0.6.4 |

---

## Push to `main`

`main` only advances through a merged pull request, which runs `ci.yml`:

```mermaid
flowchart LR
    A["Pull request"] --> B["CI (ci.yml)\n• Read-only permissions\n• Ruff lint + format check\n• Python 3.12 & 3.13 test matrix\n• CI Gate"]
    B --> C["Merge to main"]
```

No workflow bumps the version or creates a tag on push. Releases start from
`scripts/release.py` on a maintainer's machine, which opens a release PR and, after
the merge, pushes the tag (see [RELEASING.md](RELEASING.md)).

### `paths-ignore` Behavior

The push trigger ignores changes restricted strictly to documentation and reference directories:
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
- **Doc-only pushes** to `main` (`docs/`, `README.md`, etc.) skip CI. **Pull requests are never filtered**: `CI Gate` is a required check, so a workflow skipped by `paths-ignore` would leave the PR permanently unmergeable.
- **Dependency & lockfile updates** ([`uv.lock`](file:///home/dikka/Documents/01-Projects/27-SkillManager/skill-manager/uv.lock)) or code changes are **not** ignored, so the full gate runs.

---

## Branch Protection

`main` is protected by the repository ruleset `main` (id `25431580`), active since
2026-10-20:

| Rule | Effect |
|---|---|
| `deletion` | `main` cannot be deleted |
| `non_fast_forward` | force-pushes are rejected — for everyone, including the owner |
| `pull_request` | changes must arrive through a pull request; 0 approvals required |
| `required_status_checks` → `CI Gate` | a pull request cannot merge until `lint` and both test jobs pass |

There are deliberately **no bypass actors**, so `current_user_can_bypass` is
`never`. The owner merges their own pull requests rather than pushing to `main`;
no approval count is set because GitHub does not let an author approve their own
pull request.

Two platform constraints shaped this configuration:

- **No bot bypass exists on a user-owned repository.** GitHub rejects the GitHub
  Actions integration as a ruleset bypass actor — *"Actor GitHub Actions
  integration must be part of the ruleset source or owner organization"* — and
  classic branch protection rejects bypass lists outright — *"Only organization
  repositories can have users and team restrictions"*. That rules out the
  "workflow pushes straight to `main`" model, which is why releases go through a
  PR opened by `scripts/release.py`.
- **`required_status_checks` gates direct pushes, not just merges.** A push is
  rejected with *"push declined due to repository rule violations"*, because the
  new commit cannot already have reported the check. Consequence: `ci.yml` must
  run on **every** pull request, with no `paths-ignore` on `pull_request`.

To relax this later, add a `bypass_actors` entry with
`bypass_mode: "always"` for the repository-admin role — at the cost of allowing
direct pushes (and force-pushes) again.

## Secret Inventory

| Secret | Purpose | Required |
|---|---|---|
| `GITHUB_TOKEN` | Default token for releases | Yes (auto-provided) |
| `WIN_PFX_B64` | *Retired* — the legacy signing bundle was removed with the 2026-10-19 repository recreation; Windows signing awaits SignPath | No |
| `WIN_PFX_PASS` | *Retired* — passphrase for the removed signing bundle | No |

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

No repository-level permission changes are needed. The repository runs with
GitHub's default **read-only** workflow token, because every workflow declares
what it needs in its own `permissions:` block:

- `release-build.yml` — `contents: write` (create the tag and release)
- every other workflow — `contents: read`

Do **not** enable "Allow GitHub Actions to create and approve pull requests": no
workflow opens pull requests, so that setting only widens the token.

## Troubleshooting

### Windows CI fixture rules

The test jobs run on `windows-latest`, so pytest fixtures must be
portable — Linux-green tests have repeatedly broken CI:

- **No backslashes or double quotes in fixture file/dir names.**
  Backslash is a path separator on Windows (`Path("a\\b")` creates two
  levels) and `"` is illegal in Windows names (`WinError 123`). Cover
  backslash-sensitive parsing with platform-independent unit tests and
  guard fixture round-trips with
  `@pytest.mark.skipif(os.name == "nt", reason=...)`.
- **Guard `os.mkfifo` with `(OSError, AttributeError)`.** `os.mkfifo`
  does not exist on Windows — access raises `AttributeError`, not
  `OSError`.
- **Prefer the shared walk in tests too.** When asserting traversal
  behavior, compare against `iter_relative_files()` rather than a
  second inline `os.walk` reference where possible.

### Coverage below threshold
Check `tests/test_coverage_boost.py` for uncovered modules. Add targeted tests for the lowest-coverage source files.

### Pull request changes never trigger CI
A `pull_request:` trigger whose body is empty or comment-only is parsed as null,
and GitHub then silently creates **no run**: the PR reports *"no checks reported"*
and can never satisfy the required `CI Gate` check. Keep an explicit mapping:

```yaml
pull_request:
  types: [opened, synchronize, reopened]
```

### Release not published after tagging
Check that the tag reached the remote (`git ls-remote --tags origin`) and that
`release-build.yml` ran for it. The version is never bumped on push — run
`uv run python scripts/release.py <bump>`, which creates and pushes the tag.

### Artifact upload fails
Check the specific build job logs in the [release workflow](https://github.com/dishanagalawatta/SkillManager/actions/workflows/release-build.yml).
