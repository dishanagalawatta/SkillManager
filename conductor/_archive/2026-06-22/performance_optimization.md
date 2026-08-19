# Plan: SkillManager Performance Optimization

> Historical plan — preserved for traceability. See
> [`conductor/tracks.md`](tracks.md) for the active track record.

**Status:** Historical (completed) · **Date:** unknown

## Objective

Improve the responsiveness, startup time, and general performance of SkillManager by offloading heavy tasks to background threads, parallelizing discovery, and implementing deeper caching.

## Scope

- **In:**
  - Offloading fuzzy search matching to a background thread.
  - Adding search debouncing to the QML search input.
  - Parallelizing `DiscoveryService` using `ThreadPoolExecutor`.
  - Enhancing `diskcache` usage to store fully normalized skill dictionaries.
  - Optimizing `categorizer.py` regex performance.
  - Implementing targeted model updates after file operations (deletion/sync).
- **Out:**
  - Replacing the entire search engine with SQLite (deferred for now).
  - Major UI refactorings.

## Action Items

### Phase 1: Search & UI Responsiveness
- [ ] **Implement Search Debouncing**: Add a 200ms `Timer` to `GlassSearchInput.qml` to prevent executing search on every keystroke.
- [ ] **Threaded Fuzzy Search**: Refactor `SkillModel._apply_filter` to run the `SearchEngine.query` in a background thread (using `QtAsyncio` or `task_runner`).
- [ ] **Incremental Indexing**: Update `SearchEngine` to allow adding/removing single items without a full rebuild.

### Phase 2: Parallel Discovery & Deep Caching
- [ ] **Parallelize Discovery**: Modify `DiscoveryService.discover_all` to use `ThreadPoolExecutor` for scanning multiple sources and project folders concurrently.
- [ ] **Deep Object Cache**: Update the discovery cache to store fully normalized skill dictionaries (including transformed fields) to bypass `transform_skill` and frontmatter parsing for unchanged files.
- [ ] **Parsing Optimization**: Refactor `categorizer.py` to use a more efficient keyword matching strategy (e.g., a single combined regex or a trie-based approach).

### Phase 3: Targeted Operations
- [ ] **Optimistic Deletion**: Update `OpsController.deleteSkills` to remove items from the models immediately and perform targeted cache updates instead of triggering a full `refreshSkills`.
- [ ] **Targeted Sync Updates**: Ensure `UpdateController` updates only the affected skill items in the model after a successful sync.

### Phase 4: Validation
- [ ] **Verification**: Run `pytest` to ensure search filters, discovery, and file operations still work correctly.
- [ ] **Performance Audit**: Measure startup time and search latency (frames per second while typing) before and after changes.

## Verification

- Use `pytest-qt` to verify that UI remains responsive during search and discovery.
- Verify that `diskcache` correctly identifies file changes (mtime/size) and invalidates old entries.
- Test edge cases where files are deleted or moved while the app is running.

## Cross-references

- Workflow: [`conductor/workflow.md`](workflow.md)
- Active tracks: [`conductor/tracks.md`](tracks.md)
- ADRs: [`../ADR_INDEX.md`](../ADR_INDEX.md)
