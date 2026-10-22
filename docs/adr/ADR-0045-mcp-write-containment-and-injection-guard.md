# ADR-0045: MCP Tool Containment and Input-Injection Guard

> Status: **Accepted**
> Date: 2026-10-22
> Owner: @DIKKA

Related: [ADR-0040](ADR-0040-mcp-stdio-transport-anyio.md),
[ADR-0041](ADR-0041-headless-qml-introspection-mcp.md)

## Context

The stdio MCP server (`uv run skill-manager --mcp`) exposes mutating tools
(targeted installs, Write-mode file tools gate behind `--mcp-allow-write`)
and, on the automation side, real keyboard/mouse injection helpers. An audit of
the original implementation found three structural risks:

1. **No write containment.** Mutating helpers resolved user-supplied paths
   before touching disk without proving the result stayed inside a configured
   skill source. A crafted path (absolute path, `..` traversal, or a symlink
   planted outside the sources) could move or delete files near the library
   rather than inside it.
2. **Injection safety was decided in several places.** The refuse-under-pytest
   rules were checked ad hoc in platform modules; tests needed to know which
   platform module to patch, and a patch on the wrong module left the real
   `ydotool`/`keybd_event` path live against the user's desktop.

## Decision

1. **Write containment is a dedicated module.** `mcp/bridge/_guard.py`
   resolves a target against the real filesystem (symlinks included) and is
   the single choke point every mutating bridge helper in `_skills.py` must
   pass before touching disk. Helpers fail closed with a structured error.
2. **Input injection has one source of truth.** `utils/input_guard.py`
   (`injection_allowed()`, `injection_refused_reason()`) encodes the env guard
   (pytest/offscreen) *and* checks the requesting process actually owns a
   live SkillManager GUI window. `utils/linux.py` and `utils/win32.py` call it
   and never decide independently. Tests patch `skill_manager.utils.input_guard`.
3. **Slow tools stay off the transport loop.** Bridge helpers that trigger a
   scan or do blocking I/O are `async` and dispatch work via
   `asyncio.to_thread`, honoring the `anyio` transport decision (ADR-0040).

## Consequences

### Positive

- A crafted target path cannot escape the configured sources; containment is
  testable in isolation (`tests/test_mcp_safety_guards.py`).
- Injection can no longer fire from tests or CI, and a test that patches the
  wrong platform module cannot silently bypass the guard (the guard is on the
  shared module both platforms dispatch through).
- No accidental event-loop blockage during long scans or lint/test runs.

### Negative

- One extra resolution step on every mutating call (negligible: one
  `realpath`-based walk per operation).
- Tests must patch a specific module instead of the platform one they expect,
  which is the deliberate constraint this ADR encodes.

### Neutral

- Containment and the injection guard live outside the tool layer, so tool
  definitions stay declarative.
