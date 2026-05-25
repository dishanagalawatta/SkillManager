# Semantic Versioning Tagging Guide: `x.y.z-dev.n`

This document outlines the standard behavior, state transitions, and edge-case handling for the `x.y.z-dev.n` pre-release versioning scheme under the Semantic Versioning (SemVer 2.0.0) standard utilized in this repository.

## Core Principle

A pre-release tag always targets the **upcoming** release. 
For example, `1.2.4-dev.1` signifies the first development build working *towards* the stable `1.2.4` release. It has a lower precedence (is mathematically older) than the final `1.2.4` version.

---

## 1. Version Bump State Machine (Trigger Words)

Releases are triggered automatically via GitHub Actions based on specific keywords in your commit messages. Append these tags to your commit messages to drive the release cycle.

**Assumption:** The current stable release in production is `1.2.3`.

| Current State | Commit Tag | Resulting State | Description & Automation Logic |
| :--- | :--- | :--- | :--- |
| **`1.2.3`** *(Stable)* | `[dev]` | `1.2.4-dev.1` | Initializes a dev cycle targeting the next patch. Sets `n=1`. |
| **`1.2.3`** *(Stable)* | `[patch]` | `1.2.4` | Standard SemVer patch increment. |
| **`1.2.3`** *(Stable)* | `[minor]` | `1.3.0` | Standard SemVer minor increment. Resets `z` to `0`. |
| **`1.2.3`** *(Stable)* | `[major]` | `2.0.0` | Standard SemVer major increment. Resets `y` and `z` to `0`. |
| | | | |
| **`1.2.4-dev.2`** *(Dev)* | `[dev]` | `1.2.4-dev.3` | Increments the pre-release counter `n`. Continues current cycle. |
| **`1.2.4-dev.2`** *(Dev)* | `[patch]` | `1.2.4` | **Graduation:** Drops the `-dev.n` suffix. Finalizes the target patch. |
| **`1.2.4-dev.2`** *(Dev)* | `[minor]` | `1.3.0` | Skips `1.2.4`. Bumps the minor version and resets `z` to `0`. |
| **`1.2.4-dev.2`** *(Dev)* | `[major]` | `2.0.0` | Skips `1.2.4`. Bumps the major version. Resets `y` and `z`. |

*(Note: The automation enforces these exact tags for commands).*

---

## 2. Edge Cases and Complex Behaviors

The CI/CD pipeline enforces strict state management to prevent corrupted histories.

### A. Pivoting the Release Scope (Scope Creep)
**Scenario:** You are iterating on a patch branch (`1.2.4-dev.2`), but a new feature is merged, necessitating a minor release bump instead of a patch.
* **Tag Needed:** `[preminor]`
* **Resulting State:** `1.2.4-dev.2` → `1.3.0-dev.1`.
* **Behavior:** The system recognizes the shift in the target (`1.3.0`) and resets the `dev.n` counter back to `1`. (Similarly, `[premajor]` handles a shift to a major release).

### B. The "Pre-Release to Pre-Release" Cross-Grade Guard
**Scenario:** The system is currently at `1.3.0-dev.2` (working towards a minor release), and a `[patch]` tag is pushed.
* **System Behavior:** The GitHub Actions workflow will strictly fail with a **Cross-grade detected** error.
* **Rationale:** Graduating a minor pre-release (`1.3.0-dev.2`) via a patch command would result in `1.3.1`, skipping `1.3.0` entirely. This breaks the sequential release history and violates standard SemVer flows.

### C. One-Indexing for `n`
The automation enforces 1-indexing for all pre-release tags (e.g., `1.2.4-dev.1`). This is semantically clearer for tracking "Build 1" and prevents boolean falsy evaluation issues across deployment scripts.

### D. Sorting and Precedence Rules
Pre-release versions always have *lower* precedence than their standard counterpart (`1.2.4-dev.1` < `1.2.4-dev.2` < `1.2.4`). We exclusively use the `-dev.n` format to prevent alphanumeric sorting anomalies across PyPI, GitHub Releases, and local environments.
