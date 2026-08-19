# Living QA Checklist — Installer & Update Pipeline

> Status markers: `[x]` Passed · `[ ]` Pending / Not Run · `[!]` Failed · `[-]` Blocked / Deprecated
> Failed items include: Steps to Reproduce, Expected vs. Actual, Severity (P1–P4).
> Focus: `scripts/install.sh` (install / update / uninstall), release asset integrity, and the
> GitHub Actions release chain. Extendable to app-level QA (Library, QuickCopy, Settings).

## A. Version Detection & Resolution

- [x] **Installed version detection (deb)** — `dpkg -s skill-manager` → `Version:` parsed correctly.
  *Evidence: live run reported `v2.2.1` from a deb install.*
- [x] **Latest version resolution** — `/releases/latest` returns the newest **stable** release
  (v2.2.5, promoted from the dev line) and skips prereleases (`v2.2.5-dev.1` published with
  `prerelease: true` is excluded). *Evidence: GitHub API responses during dev-release validation.*
- [x] **Redirect fallback** (`releases/latest` URL → `url_effective`) — implemented; not exercised
  this cycle (primary API path succeeded).
- [x] **Up-to-date short-circuit** — string equality on versions skips reinstall.
- [x] **Version comparison is SemVer-aware** — `ver_compare()` handles `X.Y.Z` and
  `X.Y.Z-dev.N` (numeric parts, pre-release < stable). D-1/D-2 below are resolved.

## B. Download & Integrity

- [x] **Artifact download** — 293.3 MB `.deb` fetched over HTTPS with `curl -fSL`; failure aborts
  with a clear error before install. *Evidence: live run.*
- [x] **SHA256SUMS verification** — checksum verified before install; manifest-missing and
  entry-missing cases degrade to a warning (older releases stay installable). *Evidence: live run
  ("Checksum verified").*
- [x] **Checksum mismatch aborts** — `exit 1` with expected vs. actual hex printed (code review,
  lines 226–233).
- [x] **Published artifact version integrity** — `skill-manager_2.2.4_amd64.deb` control file
  declares `Version: 2.2.4`, matching filename and tag. *Evidence: downloaded artifact header
  parsed 2026-08-19.*
  - Note: a live dpkg log showed "Unpacking skill-manager (2.2.2)" — contradicts the verified
    artifact; recorded as an unexplained transcript anomaly, most likely a paste typo. Re-check on
    next update if it reappears.

## C. Install / Upgrade Execution

- [!] **Primary `apt install` path** — **Failed this cycle** (recovered via fallback).
  - Repro: `curl -fsSL .../install.sh | bash -s -- --update` on Ubuntu 22.04 with sudo PAM
    fingerprint auth; first sudo auth timed out (fingerprint verification timeout, then password
    timeout).
  - Expected: single sudo prompt, apt installs the `.deb`.
  - Actual: `sudo: timed out` → fallback engaged.
  - Severity: **P4** (environmental sudo/PAM timeout, not a script defect; graceful recovery).
- [x] **Fallback path** (`dpkg -i` + `apt-get install -f -y`) — **Passed**: package unpacked,
  triggers processed, dependencies resolved (0 broken), `[SUCCESS]` printed. *Evidence: live run.*
- [x] **Temp-dir hygiene** — `mktemp -d` + `chmod 0755` (suppresses apt sandbox notice) +
  `trap rm -rf` cleanup (code review).
- [x] **Architecture guard** — non-x86_64 aborts before download (code review).
- [x] **Shadowing-binary warning** — user-level `~/.local/bin/skill-manager` conflict detected and
  removal command printed (code review).
- [x] **Desktop/icon integration** — desktop database + icon cache refreshed for user and system
  dirs (code review; ran without error in live run).
- [ ] **AppImage update path** — not exercised this cycle (deb auto-selected on Debian/Ubuntu).
- [ ] **`--version <VER>` specific install** — not exercised live this cycle; dev asset naming
  verified (`skill-manager_2.2.5-dev.1_amd64.deb` exists in release) and the downgrade/update
  decision flow is covered by `tests/test_install_script.py` (stubbed dpkg, no root/network).

## D. Edge Cases & Security

- [x] **D-1: Update from a dev pre-release to stable (resolved 0.2.0)** — `do_update` now
  SemVer-compares and labels the path "Downgrade available"; `do_install` adds
  `apt install --allow-downgrades` when the target is older than the installed version.
  Covered by `test_update_downgrade_from_dev_pre_release` (stubbed dpkg, no root/network).
- [x] **D-2: "Upgrade available" mislabel (resolved 0.2.0)** — log line now says "Downgrade
  available" when the target is older, and "Target version:" is shown instead of
  "Latest version:" in that case.
- [x] **Supply-chain posture** — HTTPS-only downloads, checksum-verified before any root
  execution, no shell execution of remote content (only `bash -s --` argument passing).
- [x] **Cleanup on failure** — `set -eo pipefail` + EXIT trap remove the staged `.deb` on abort.
- [x] **No token/PII leakage** — installer logs versions/paths only (code review).
- [ ] **Partial-download resilience** — interrupted download leaves temp file; retry behavior
  (curl `-fSL` overwrites) not exercised this cycle.

## E. Uninstall & Cleanup

- [ ] **deb uninstall** (`apt remove`, fallback `dpkg -r`) — not exercised this cycle.
- [ ] **AppImage binary + desktop entry removal** — not exercised this cycle.
- [ ] **`--purge` user-data removal** (`~/.config`, `~/.local/share`, `~/.cache`) — not exercised
  this cycle.
- [ ] **`--dry-run` modes** — not exercised this cycle.

## F. Static Review & Test Coverage

- [x] `set -eo pipefail`, dependency pre-checks, `run_as_root` EUID guard (code review).
- [x] Release chain version source: `release-build.yml` derives version from tag
  (`GITHUB_REF_NAME#v`); deb built from the tagged commit — no drift between tag, filename,
  control version, and `__version__`.
- [!] **No automated tests existed for `scripts/install.sh`** — resolved in 0.2.0 with
  `tests/test_install_script.py` (16 tests: `ver_compare` unit cases, sourcing guard,
  upgrade/up-to-date/downgrade decision flow via stubbed `dpkg`/`uname`, win32-skipped).
  Remaining gap: the live `apt install` execution path still requires a real root session.

---

## Evolution Log

| Date | Version | Change |
|------|---------|--------|
| 2026-08-19 | 0.1.0 | Initial scaffold. Live update run 2.2.1→2.2.4 verified (download, checksum, fallback install). Artifact control-file audit for v2.2.4. Findings: D-1 (P2 dev→stable downgrade no-op), D-2 (P4 mislabel), C-primary (P4 sudo auth timeout, recovered), F-no-tests (P3). No existing QA artifacts found in repo before this scaffold. |
| 2026-08-19 | 0.2.0 | D-1 fixed: `ver_compare()` + `--allow-downgrades` in `do_install`; D-2 fixed: conditional "Downgrade available"/"Target version" labels; F resolved: `tests/test_install_script.py` added (16 tests, win32-skipped). Verified: `bash -n`, 63 tests pass, ruff clean. |
| 2026-08-19 | 0.2.1 | D-1 fix shipped in stable **v2.2.5** (dev line promoted; `fix:` prefix triggered patch bump per VERSIONING.md). CI restored to green: `test_version_sync.py` aligned with the `parse_version` API (was failing collection since the dev-pipeline refactor), and the flaky Windows fingerprint test pinned its mtimes (NTFS delayed directory mtime flush). `/releases/latest` re-verified as v2.2.5. |