# Plan: Professional Codebase Cleanup (v1.8.0)

Full plan: `.omo/plans/refactor-codebase.md` (Momus-approved 2026-08-01).
Scope: hygiene + god-file decomposition + test consolidation + module dedup.
Philosophy: split + fix issues found. QML surface frozen.

## Phase 0 — Safety net: hygiene + flaky-test fixes (current)

- [ ] 1. Conductor track created (this track)
- [ ] 2. pyproject.toml: remove stray blank lines
- [ ] 3. Add .gitattributes (LF/CRLF policy)
- [ ] 4. requirements.txt: keep as-is (documented generated artifact)
- [ ] 5. Move time_quick_copy.py → scripts/diagnostics/
- [ ] 6. Fix xdist flakiness (test_analytics.py, test_discovery_integration.py)
- [ ] 7. Delete dead core/updater.py; migrate 4 tests to copier
- [ ] 8. Gate: ruff clean, suite green (serial + -n auto), coverage >=80, commit

## Phase 1 — app.py decomposition (2,212 → ~1,000)

- [ ] 9. Extract utils/native_styling.py (pywinstyles, DWMWA, _apply_immersive_dark)
- [ ] 10. Extract utils/single_instance.py (_bring_existing_window_to_front, _acquire_linux_lock)
- [ ] 11. Extract controllers/command_channel.py (CommandChannel L136-333)
- [ ] 12. Extract mcp/launcher.py (_run_mcp_mode) + bootstrap.py (main() split)
- [ ] 13. Rewrite source-text tests (test_single_instance_guard, test_shutdown, test_app_initialization, test_app_dark_mode_native) + gate + commit

## Phase 2 — mcp/bridge.py package (1,797)

- [ ] 14. Convert to mcp/bridge/ package: _controller/_skills/_state/_static/_jobs/_devtools/_win32/_capture/_ipc/_input + facade __init__.py
- [ ] 15. Update test patch targets (test_mcp_bridge.py, test_mcp_screenshot.py) + gate + commit

## Phase 3 — ops_controller.py package (1,788)

- [ ] 16. controllers/ops/ package: toggles/delete/copy/clipboard/commands/inspector/sync + facade
- [ ] 17. Fix dead errorOccurred signal, DiscoveryService factory, _emit_missing_skills_prompt dup, tokenizer dup + .pyi refresh + gate + commit

## Phase 4 — qt_model.py + config_controller.py mixins (1,241 + 1,180)

- [ ] 18. core/models/: roles/selection/pipeline/incubation/collapse/ingest mixins; ConfigController: settings/sources/projects/shortcuts/collections/collection_shortcuts/diagnostics mixins
- [ ] 19. .pyi lockstep + QML smoke + gate + commit

## Phase 5 — Test suite consolidation

- [ ] 20. Merge one-off regression files into themed suites; dedupe fixtures; prune overlap; coverage >=80 gate + commit

## Phase 6 — Core module dedup

- [ ] 21. update_single_package shared helper; triple path detection consolidation + gate + commit

## Phase 7 — Docs + final gate

- [ ] 22. ARCHITECTURE/README updates, .pyi verification, archive track, final gate + smoke tests
