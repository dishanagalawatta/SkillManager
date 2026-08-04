# Plan: MCP Server for SkillManager

Design locked — see `docs/MCP_SERVER.md`. Native Python `mcp` SDK server, stdio
transport, launched via `uv run skill-manager --mcp`. Bridges in-process to
`AppController` + sub-controllers. Headless (no QML engine) for fast/CI-friendly
startup. Write tools gated behind `--mcp-allow-write`.

## Tasks

- [ ] 1. Add `mcp` SDK dependency to `pyproject.toml` + verify `uv sync`
- [ ] 2. `mcp/models.py` — pydantic request/response schemas for all tools
- [ ] 3. `mcp/bridge.py` — thin wrappers over AppController + sub-controllers (headless construct)
- [ ] 4. `mcp/tools/build.py` — sm_lint, sm_run_tests, sm_build (async via BackgroundTaskRunner)
- [ ] 5. `mcp/tools/analyze.py` — sm_list_skills, sm_list_sources, sm_list_projects, sm_static_analyze
- [ ] 6. `mcp/tools/monitor.py` — sm_get_diagnostics, sm_get_health, sm_tail_events
- [ ] 7. `mcp/tools/debug.py` — sm_dump_state, sm_inspect_controller, sm_capture_errors
- [ ] 8. `mcp/tools/write.py` — sm_delete_skill, sm_deploy (gated --mcp-allow-write, AGENTS.md exclusions)
- [ ] 9. `mcp/server.py` + `mcp/__init__.py` — MCPServer factory, stdio transport, `--mcp` wiring in `app.py`, safe_tool decorator, job polling (sm_job_status)
- [ ] 10. Tests `tests/test_mcp_*.py` — unit (mocked AppController) + in-process integration over stdio pipe; 80% coverage
- [ ] 11. Docs — README dev section + AGENTS.md quick-ref table + `.mcp.json` example in docs/MCP_SERVER.md

## Notes

- Headless: construct AppController without QQmlApplicationEngine (controllers are plain QObjects).
- Own mutex `SkillManagerMcpMutex` so --mcp never fights the GUI instance.
- Every tool call → capture_event("mcp_tool_call", {tool, args}).
- Respect AGENTS.md exclusions in write.py (TODO.md, .agents/commands, .agents/skills).
- Follow TDD: tests before/with implementation per conductor-implement.

## Decisions (from design lock)

- Native Python mcp SDK, stdio (not C++ refs, not hosted docs MCP).
- In-process --mcp mode (not out-of-process IPC).
- Full lifecycle tools (build+analyze+monitor+debug).
- Write tools gated --mcp-allow-write.

## Follow-up: Performance profiling & optimization (2026-07-20)

Used the MCP server + a headless profiling harness (`scripts/_profile_harness.py`)
to measure the discovery pipeline on real data (237 skills, 1 source, 7 projects).

### Findings (baseline)
| Stage | Time | Verdict |
|-------|------|---------|
| `discover_all` full scan | ~4590 ms | dominant one-time cost (first run / `force_full_scan`) |
| `discover_all` incremental | ~566 ms | everyday cost |
| └ `load_cache` JSON | ~135 ms | re-parses full CacheState every refresh |
| └ `compute_dir_fingerprint` ×8 dirs | ~95 ms | **~95% is redundant `_hash_child_names` (iterdir+sort+sha1) on unchanged dirs** |
| `Skill.from_dict_fast` ×237 | ~8 ms | fine |
| `FilterEngine` ×2 | ~1.5 ms | fine |
| `SearchEngine` build | ~9 ms | fine |
| `SkillModel.replacePreparedState` | ~0.4 ms | fine |

Bottleneck = filesystem scan + per-refresh fingerprinting. Model/engine layers already optimal.

### Changes
- **`mcp/tools/monitor.py`**: added `sm_profile` (read-only) — runs the discovery
  pipeline with per-stage `time.perf_counter()` timing and reports the identified
  bottleneck. Satisfies "add missing measurement tools". `force_full_scan` arg
  measures the cold path too.
- **`core/discovery.py`**: `compute_dir_fingerprint` now memoizes by
  `(normcase path -> (mtime,size,skill_count,max_sub_mtime), fingerprint)`. When the
  cheap prefix is unchanged, the expensive `_hash_child_names` is skipped. Fingerprint
  string format unchanged → existing diskcache fingerprints still compare correctly.

### Result (this machine)
- Full scan: 4592 ms → ~994 ms (warm diskcache + memo).
- Incremental: 566 ms → ~259 ms.

### Tests added
- `tests/test_mcp_tools.py` — `sm_profile` (cached + full-scan + schema).
- `tests/test_discovery_fp.py` — memo hit/miss, correctness vs baseline formula,
  normcase keying, no cross-dir leakage.

### Note on CI
`test_rebuild_cache_clears_json_index` fails under `pytest -n auto --dist loadfile`
(full suite) but passes in isolation and with neighbors — pre-existing environmental
failure (shared real `DATA_DIR` diskcache), confirmed independent of this work
(reproduces with memo disabled and on original code). Not a regression.
