---
name: skillmanager-mcp
description: Use this skill when an agent needs to connect to or drive the SkillManager desktop app via its MCP server (uv run skill-manager --mcp). Covers client setup (.mcp.json), full tool catalogue (skills, build, analyze, monitor, debug, write), write-mode gating, and response envelopes for any coding agent.
risk: medium
source: project
---

# SkillManager MCP Server

SkillManager ships a native Python MCP server (stdio, `mcp` SDK) that lets AI coding agents search, read, create, update, deploy, delete, and analyze agent skills — without shelling out or opening a GUI.

## When to Use

- An agent needs to search, read, inspect, or manage skills across projects and source directories.
- An agent needs to build, lint, test, or analyze the SkillManager codebase.
- An agent needs to inspect running app state (health, diagnostics, loaded skills/projects).
- An agent needs to create, update, deploy, or delete skills safely (with write mode enabled).

## Launch / Connect

The server runs headless (own mutex, never collides with a running GUI instance). An agent connects by launching the server executable. Point the client at the repo launcher script (it invokes the project venv directly, so `uv` does not need to be on the client's PATH):

```json
{
  "mcpServers": {
    "skillmanager": {
      "command": "/path/to/skill-manager/scripts/mcp_launcher.sh",
      "args": ["--mcp"]
    },
    "skillmanager-write": {
      "command": "/path/to/skill-manager/scripts/mcp_launcher.sh",
      "args": ["--mcp", "--mcp-allow-write"]
    }
  }
}
```

- `skillmanager` — Read-only tools (`sm_list_skills`, `sm_get_skill`, `sm_search_skills`, `sm_sync_skills`, build/analyze/monitor/debug).
- `skillmanager-write` — Same plus mutating tools (`sm_create_skill`, `sm_update_skill`, `sm_delete_skill`, `sm_deploy`).

## Tools Reference

All tools use the prefix `sm_`. Every response is wrapped in a uniform JSON envelope:
`{"ok": bool, "tool": str, "data"?: ..., "error"?: str}`.

### Skill Management (Read-Only)
| Tool | Args | Description |
|------|------|-------------|
| `sm_list_skills` | `{include_commands?, project_label?}` | Enumerate all discovered skills in library model. |
| `sm_get_skill` | `{skill_id}` | Retrieve full skill details (metadata, SKILL.md body, file listing). |
| `sm_search_skills` | `{query, category?, project_label?, include_commands?, limit?}` | Search skills by keyword in name, category, description, tags, or content. |
| `sm_sync_skills` | `{force_full_scan?}` | Re-scan skill source directories and target projects into library model. |
| `sm_list_sources` | `{}` | List configured skill source directories. |
| `sm_list_projects` | `{}` | List configured target project directories. |

### Skill Management (Mutating — `--mcp-allow-write` required)
| Tool | Args | Description |
|------|------|-------------|
| `sm_create_skill` | `{name, content, source_path?, description?, category?}` | Create a new skill directory with SKILL.md. |
| `sm_update_skill` | `{skill_id, content?, description?, category?}` | Update an existing skill's SKILL.md file or metadata. |
| `sm_deploy` | `{skill_id, target}` | Deploy a skill to a target project directory (`<target>/.agents/skills/`). |
| `sm_delete_skill` | `{skill_id}` | Delete a skill folder/file (refuses protected AGENTS.md paths). |

### Build & Dev Tools
| Tool | Args | Description |
|------|------|-------------|
| `sm_lint` | `{path?, fix?}` | Run `uv run ruff check [--fix] <path>`. Returns lint pass status, stdout, stderr. |
| `sm_run_tests` | `{target?, parallel?}` | Run pytest suite. Returns `job_id` for async polling. |
| `sm_build` | `{target?}` | Run application builder (`uv run skill-manager-build`). Returns `job_id`. |
| `sm_job_status` | `{job_id}` | Poll background job status/results (`running`, `done`, `error`). |

### Analysis & Debugging
| Tool | Args | Description |
|------|------|-------------|
| `sm_static_analyze` | `{pattern, path?}` | Regex grep over codebase (gitignore-aware). |
| `sm_get_health` | `{}` | Application & bridge health status snapshot (includes `qml.enabled/loaded/error`). |
| `sm_get_diagnostics` | `{limit?}` | Read recent diagnostic ring-buffer entries. |
| `sm_dump_state` | `{}` | Export safe subset of controller & model configuration state. |
| `sm_detect_qml_errors` | `{limit?}` | Scan the diagnostic buffer for QML/JavaScript errors. |
| `sm_get_performance_metrics` | `{}` | Memory, CPU, thread count, PID, uptime. |

### UI Inspection & Visual Verification
These work with **no GUI running**: in `--mcp` mode the first call lazily loads
`Main.qml` on the offscreen platform plugin (~1.7 s, one-time) and renders it
headlessly. Nothing is ever painted on your desktop, and the headless process
never writes your UI state back to `config.json`. Set `SKILL_MANAGER_MCP_NO_IPC=1`
to keep the server from talking to a running GUI at all (it then refuses with
`ipc_disabled` and uses the headless render).

| Tool | Args | Description |
|------|------|-------------|
| `sm_screenshot` | `{navigate?, save?, width?, height?}` | Capture the window as base64 PNG. `data.source` is `live-gui`, `native` or `headless-qml`. |
| `sm_inspect_qml_tree` | `{max_depth?}` | QML object tree (names, classes, geometry, `child_count`); returns `root_count`/`node_count`. |
| `sm_accessibility_audit` | `{max_depth?}` | Audit the tree for missing roles/names and unlabeled buttons. |
| `sm_get_current_view` | `{}` | Active view (`Library` / `QuickCopy` / `Updates` / `Settings`). |
| `sm_get_pixel_color` | `{x, y}` | RGB/hex color of a pixel in the captured window. |
| `sm_find_visual_issues` | `{image_b64?, check_*?}` | Clipping/contrast/overlap scan; omit `image_b64` to analyse the current window. |
| `sm_compare_screenshot` | `{baseline_b64?/baseline_name?, current_b64?, threshold?}` | Structural + perceptual (pHash) diff against a baseline. |
| `sm_run_ui_scenario` | `{scenario}` | Run `navigate_library` / `navigate_quickcopy` / `navigate_updates` / `navigate_settings` / `full_tour`, verifying each step (`in_process`, `verified`). |
| `sm_get_frame_timing` | `{duration_s?, force_render?}` | Frame durations; `mode` is `natural` / `forced_60hz` / `unavailable` / `invalid`. Idle UIs report 0 frames unless `force_render=true`. |
| `sm_measure_startup_time` | `{}` | Time headless controller access; ms + timestamp. |

## Safety & Exclusion Rules

1. **Write tools require `--mcp-allow-write`.** Without this flag, mutating tools return `{"ok": false, "error": "write mode disabled..."}`.
2. **AGENTS.md Exclusions.** Mutating tools strictly refuse paths containing `TODO.md`, `.agents/skills`, or `.agents/commands`.
3. **No Unsafe Fallbacks.** Unresolvable skill IDs return `ok=false` with descriptive error messages instead of corrupting paths.

## Quick Reference

- Read-only: `uv run skill-manager --mcp`
- Write mode: `uv run skill-manager --mcp --mcp-allow-write`
- Full documentation & setup guides: `docs/MCP_SERVER.md`
