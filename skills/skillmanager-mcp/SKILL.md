---
name: skillmanager-mcp
description: Use this skill when an agent needs to connect to or drive the SkillManager desktop app via its MCP server (uv run skill-manager --mcp). Covers client setup (.mcp.json), the full tool catalogue, write-mode gating, and the response envelope so any coding agent can build, analyze, monitor, debug, or (with --mcp-allow-write) mutate skills safely.
risk: medium
source: project
---

# SkillManager MCP Server

SkillManager ships a native Python MCP server (stdio, `mcp` SDK) that lets a coding
agent introspect and drive the live app — skills, sources, projects, diagnostics,
controller health, and (write mode) skill deletion — without shelling out or booting a GUI.

## When to Use

- The user wants an agent to build, lint, test, or analyze the SkillManager codebase.
- The user wants to inspect running app state (health, diagnostics, loaded skills/projects).
- The user wants to debug the app (dump state, inspect a sub-controller's surface, capture errors).
- The user asks an agent to delete/deploy a skill and has explicitly enabled write mode.

## Launch / Connect

The server runs headless (own mutex, never fights a running GUI instance). An agent
connects by having its MCP client launch the server. Drop this `.mcp.json` at the
**project root** so `uv` resolves the workspace:

```json
{
  "mcpServers": {
    "skillmanager": {
      "command": "uv",
      "args": ["run", "skill-manager", "--mcp"]
    },
    "skillmanager-write": {
      "command": "uv",
      "args": ["run", "skill-manager", "--mcp", "--mcp-allow-write"]
    }
  }
}
```

- `skillmanager` — read-only tools (build / analyze / monitor / debug).
- `skillmanager-write` — same plus mutating `sm_delete_skill`, `sm_deploy`.

The agent must run from the project root so `uv` finds the workspace and the
`skill-manager` command is on PATH.

## Tools

All tools are prefixed `sm_`. Every response is a JSON envelope:
`{"ok": bool, "tool": str, "data"?: ..., "error"?: str}`. On unknown tool or
exception, `ok=false` with a descriptive `error`.

### Build / Dev (read-only)
| Tool | Args | Does |
|------|------|------|
| `sm_lint` | `{path?, fix?}` | Run `uv run ruff check [--fix] <path>`. Returns `passed`, `returncode`, `stdout`, `stderr`. |
| `sm_run_tests` | `{target?, parallel?}` | Run `pytest [-n auto] [target]`. Returns `passed`, `returncode`, output. |
| `sm_build` | `{target?}` | Run `uv run skill-manager-build`. Returns `success`, `returncode`, output. |
| `sm_job_status` | `{job_id}` | Poll an async job buffer. Returns `{status, result, error}`. Unknown id → `ok=false`. |

### Analyze (read-only)
| Tool | Args | Does |
|------|------|------|
| `sm_list_skills` | `{include_commands?, project_label?}` | Skills from the library model (name, path, category, client, risk, source, flags). |
| `sm_list_sources` | `{}` | Configured skill source directories. |
| `sm_list_projects` | `{}` | Configured target project directories. |
| `sm_static_analyze` | `{pattern, path?}` | Safe regex grep over the repo (gitignore-aware). Returns `{file, line, text}` matches. Invalid regex → `ok=true` with empty matches (error is swallowed by the bridge). |

### Monitor (read-only)
| Tool | Args | Does |
|------|------|------|
| `sm_get_diagnostics` | `{limit?}` | Recent diagnostic ring-buffer events. |
| `sm_get_health` | `{}` | Health snapshot: `healthy`, `qt_loop_alive`, `controller_present`, `model_counts`, `recent_errors`. |
| `sm_tail_events` | `{limit?}` | Newest N diagnostic events. |

### Visual (read-only)
| Tool | Args | Does |
|------|------|------|
| `sm_screenshot` | `{navigate?, save?}` | Capture the live GUI window (title "Skill Manager") cross-process as a base64 PNG. Optional `navigate` (`QuickCopy`\|`Library`\|`Updates`\|`Settings`) switches the running GUI to that section first via a file-based IPC channel. `save=true` also writes the PNG to `.agents/screenshots/` and returns `save_path`. GUI not running → `ok=false`. |

### Debug (read-only)
| Tool | Args | Does |
|------|------|------|
| `sm_dump_state` | `{}` | Safe subset of `AppController` state (sources, projects, config keys, model counts). |
| `sm_inspect_controller` | `{name}` | Introspect a sub-controller's public methods + signals. Unknown name → `found=false`. |
| `sm_capture_errors` | `{limit?}` | Only error-level diagnostic events. |

### Write (gated by `--mcp-allow-write`)
| Tool | Args | Does |
|------|------|------|
| `sm_delete_skill` | `{skill_id}` | Resolve `skill_id` (name or local_path) then delegate to `OpsController.deleteSkill`. Refuses to guess an unknown path. |
| `sm_deploy` | `{skill_id, target}` | **Not implemented** in the app yet — returns `ok=false` ("deploy not yet implemented"). Do not assume it works. |

## Hard Rules (follow these)

1. **Write tools require the `-write` server.** If connected to `skillmanager`
   (read-only), `sm_delete_skill`/`sm_deploy` return
   `{"ok": false, "error": "write mode disabled … restart with --mcp-allow-write"}`.
   Do not retry against the read-only server — request write mode instead.
2. **AGENTS.md exclusions are enforced even in write mode.** `sm_delete_skill`
   refuses `TODO.md`, `.agents/skills/…`, and `.agents/commands/…` with
   `ok=false` ("refused: skill_id resolves under an AGENTS.md-excluded path.").
   Never attempt to bypass; these are protected paths.
3. **`sm_delete_skill` never guesses.** Pass a real skill name or `local_path`
   from `sm_list_skills`. An unresolvable id returns `ok=false` — do not fabricate paths.
4. **`sm_deploy` is a no-op stub.** It raises `NotImplementedError`; the tool
   reports it as `ok=false`. Treat deployment as unsupported until the app gains a deploy API.
5. **Async work uses jobs.** Long ops return a `job_id`; poll with `sm_job_status`.
   A job buffer entry is `{status: "running"|"done"|"error", result, error}`.
6. **Headless, not a GUI.** The MCP server does not open windows. Use it for
   automation/CI, not for visual interaction.

## Quick Reference

- Connect read-only: `uv run skill-manager --mcp`
- Connect with writes: `uv run skill-manager --mcp --mcp-allow-write`
- All responses are JSON envelopes with `ok`/`tool`/`data`/`error`.
- Unknown tool or bad args → `ok=false`; read `error` and adjust.
- Full design + tool reference: `docs/MCP_SERVER.md` (in the SkillManager repo).
