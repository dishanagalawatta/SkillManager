# Plan: Application Optimization & Reliability

## Approach
This plan outlines a phased approach to integrate high-performance open-source libraries into the SkillManager application. We will swap out standard library JSON/YAML parsing for faster alternatives, implement robust background task management using `PySide6.QtAsyncio`, enhance network resilience with `tenacity` (already present but will be explicitly audited/expanded), and integrate `sentry-sdk` for comprehensive crash reporting.

## Scope
- **In:**
  - Replacing standard `json` parsing with `orjson` (or `msgspec`) where appropriate.
  - Adding local caching using `diskcache`.
  - Refactoring heavy background operations (e.g., skill discovery, git syncing) to use `PySide6.QtAsyncio`.
  - Auditing/expanding `httpx` and `tenacity` usage for API and Git operations.
  - Integrating `sentry-sdk` for unhandled exception capture and telemetry.
- **Out:**
  - Major UI redesigns.
  - Complete rewrite of the Git integration (we will optimize existing logic).

## Action Items

- [ ] **Phase 1: Startup & Data Loading Optimization**
  - [ ] Add `orjson` and `diskcache` to `pyproject.toml` dependencies.
  - [ ] Refactor `src/skill_manager/core/persistence.py` and `core/parsing/` to utilize `orjson` for configuration and cache file loading.
  - [ ] Implement `diskcache` in `core/discovery.py` to cache parsed markdown/YAML results, reducing startup overhead.
- [ ] **Phase 2: UI Responsiveness**
  - [ ] Audit `src/skill_manager/utils/qt_threading.py` and `task_runner.py`.
  - [ ] Migrate the most expensive background tasks (e.g., full library rescans) to utilize `PySide6.QtAsyncio` to guarantee the main UI thread remains unblocked.
- [ ] **Phase 3: Network & Synchronization Resilience**
  - [ ] Review `src/skill_manager/core/update_service.py` and ensure all `httpx` calls are wrapped with robust `tenacity` retry decorators (handling timeouts and 5xx errors).
  - [ ] Implement timeout and retry logic around Git subprocess calls if applicable.
- [ ] **Phase 4: Crash Prevention & Stability**
  - [ ] Add `sentry-sdk` to `pyproject.toml` dependencies.
  - [ ] Initialize `sentry-sdk` in `src/skill_manager/app.py` or `__main__.py` to capture unhandled exceptions and PyQt crashes. Configure it to respect a user opt-out flag in the configuration.
- [ ] **Phase 5: Validation & Testing**
  - [ ] Run the existing test suite (`pytest`) to ensure no regressions were introduced.
  - [ ] Add specific tests verifying cache hits/misses, async task non-blocking behavior, and retry logic execution.

## Open Questions
- For `sentry-sdk`, do you have an existing DSN we should use, or should we set it up with a placeholder/environment variable for now?
- Regarding `orjson` vs `msgspec`, `orjson` is generally a drop-in replacement for `json`, while `msgspec` offers faster validation alongside parsing. Given you are already using `pydantic` for validation, `orjson` might be the simpler, faster drop-in. Do you have a strong preference?