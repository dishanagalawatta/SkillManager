# Security Policy

## Reporting Vulnerabilities

If you discover a security vulnerability, please report it via [GitHub Security Advisories](https://github.com/dishanagalawatta/SkillManager/security/advisories/new).

## Download Integrity

Every release publishes a `SHA256SUMS` manifest alongside its artifacts (`.deb`, `.AppImage`, `.exe`).

- The Linux installer (`scripts/install.sh`) verifies every downloaded artifact against this
  manifest **before** installation and **aborts** on any checksum mismatch — a corrupt or
  tampered file is never installed.
- If the manifest itself (or the artifact's entry) is unavailable — e.g. very old releases
  that predate checksums — the installer warns and proceeds, since the download still travels
  over TLS from GitHub Releases.
- Windows (`winget`) installs are verified by Microsoft's package index.

## Shell Command Construction

Package `verify_command` strings are generated from user-influenced paths
and must follow three rules (see ADR-0038; fixed in PR #285, hardened
in PR #288):

- **Quote every interpolation**: all generated paths go through
  `shlex.quote()` — including paths inside `echo` text, where double
  quotes alone do not stop shell breakout.
- **Never execute through a shell**: `run_shell_command` parses
  `test -d ... && echo ...` in pure Python
  (`intercept_cross_platform_command`) and otherwise uses
  `shlex.split(...)` with `shell=False`. There is no `shell=True` path.
- **Parse without escape processing**: the interceptor uses
  `_split_shell_like()`, which keeps backslashes literal so Windows
  paths survive on every platform. Do not "simplify" it back to
  `shlex.split` — POSIX mode eats backslashes (`C:\foo` → `C:foo`).
  Note `shlex.quote` output is POSIX-style; it is safe here precisely
  because nothing is ever executed by a real shell (it is documented
  as unsafe for `cmd.exe` / PowerShell under `shell=True`).

## Suppressed CVEs

The following CVEs are known in pinned dependencies but are **not exploitable
in this app's threat model** and are suppressed via `pip-audit --ignore-vuln`.

### CVE-2025-69872 — `diskcache 5.6.3` (pickle deserialization RCE)

- **Status**: Unfixed upstream (5.6.3 is the latest version on PyPI).
- **Pre-condition**: Attacker needs write access to the cache directory
  (`DATA_DIR/cache/discovery`).
- **Why suppressed**: This is a single-user desktop app. The cache directory
  lives in the user's own profile folder, which the user already controls.
  An attacker with write access to that folder has the user's account and can
  run code via many other vectors (startup folder, scheduled tasks, etc.).
  The CVE does not materially increase the attack surface.
- **Revisit when**: `diskcache` releases a version >= 5.6.4 with a fix.


