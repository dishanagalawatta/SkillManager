# ADR-0038: Cross-Platform `verify_command` Parsing Without Shell Escapes

> Status: **Accepted**
> Date: 2026-09-20
> Owner: @DIKKA

## Context

Generated `verify_command` strings (`test -d <path> && echo ...`) are
stored in package config and executed via `run_shell_command`. Two
defects compounded: PR #285 fixed an unquoted `{expanded}` path
interpolated inside the `echo` double quotes (command injection via
crafted paths), and the follow-up found the *parser* also unsafe —
`intercept_cross_platform_command` used POSIX-mode `shlex.split`,
which interprets backslashes outside single quotes as escapes, so
`C:\foo` parsed as `C:foo` and Windows verifications mis-reported on
every platform running the parse.

## Decision

1. **Quote every interpolation at generation**: both construction
   sites in `core/skill_packages/config.py` use `shlex.quote(expanded)`
   for every path token, including inside `echo`
   (`echo "Skills installed in " {quoted_path}`).
2. **Never execute through a shell**: `run_shell_command` handles
   `test -d ... && echo ...` in `intercept_cross_platform_command`
   (pure-Python parsing) and otherwise runs
   `shlex.split(...)` + `shell=False`. No `shell=True` path exists.
3. **Parse shell-like syntax without escape processing**:
   `_split_shell_like()` in `core/skill_packages/updater.py`
   replicates POSIX word-concatenation (adjacent quoted and bare
   sections form one word) but treats backslashes as always literal,
   so Windows paths survive on every platform. Raw `shlex.split`
   (either `posix` mode) must not be used for these strings.

## Consequences

### Positive

- The injection class from #285 is closed at generation time, and the
  parsing layer no longer corrupts the paths it verifies.
- Windows `verify_command`s work; previously any backslash path could
  false-fail verification.
- Regression tests pin both layers, including a mutation-checked
  adversarial path.

### Negative

- `_split_shell_like` is a second, narrower parser to maintain
  alongside `shlex`; it intentionally diverges from POSIX on
  backslash escapes, which must stay documented.
- User-supplied custom `verify_command`s still pass through the same
  interceptor, so exotic hand-written quoting normalizes to the same
  rules (documented, not shell-exact).

### Neutral

- `shlex.quote` output remains POSIX-style single quotes; this is
  safe because nothing is ever executed by a real shell.

## Alternatives Considered

### `shell=True` with careful quoting

Rejected: reintroduces the entire injection class and is
POSIX-only — `shlex.quote` is documented as unsafe for `cmd.exe` /
PowerShell.

### Structured verification (path + message fields)

Preferred long-term (stores data, not shell syntax), but a larger
config-schema change; deferred. This ADR is the containment fix.

## References

- PR #285 (injection fix), PR #288 (backslash parsing fix)
- Python `shlex` docs ("only designed for Unix shells"),
  `subprocess` docs (`shell=False` preference), PEP 787
