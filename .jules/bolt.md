## 2024-06-22 - rapidfuzz process.extractOne early-exit regression
**Learning:** `rapidfuzz.process.extractOne` evaluates the entire sequence to find the absolute maximum match. If the existing Python loop optimizes large list evaluations with an early exit (e.g. `if max_score > 70: break`), replacing it blindly with `extractOne` can actually cause performance regressions and functional differences.
**Action:** Always verify if the original looping logic relies on early termination thresholds. If it does, and the list size is significant, avoid `extractOne` and instead optimize the Python loop using fast-path exact substring checks before invoking expensive `fuzz.ratio` operations.
## 2026-07-10 - Fast-path exact match with list membership
**Learning:** Checking `if qt in all_doc_tokens:` where `all_doc_tokens` is a list of pre-computed string tokens acts as a fast, exact match check evaluated in C, whereas `qt in string` is a substring check. This is an optimal, fully isolated fast-path prior to executing expensive `fuzz.ratio` loops that rely on early-exit thresholds.
**Action:** When replacing loops that require early termination (`max_score > 70: break`), use list membership (`qt in list`) to short-circuit exact matches in a preliminary loop before executing the nested `fuzz.ratio` loops.
## 2025-02-14 - Cache path calculations in quick_copy.py
**Learning:** During the file discovery process and quick copying operations, `project_root_for_project` and `skill_base_relative` are called heavily on the same paths, which adds redundant path resolution overhead. Applying `@lru_cache` significantly reduces this overhead.
**Action:** Use `@lru_cache` on repetitive path resolution functions like `project_root_for_project` and `skill_base_relative` to memoize the results for hot paths.

## 2024-05-18 - Optimized file tree traversal for fast fingerprinting
**Learning:** `pathlib.Path.rglob` is significantly slower for file metadata extraction because `stat()` calls create independent system requests without utilizing the cached data from traversal.
**Action:** Replace `rglob` with an optimized recursive `os.scandir` implementation. Access `entry.stat()` directly to reuse system call results from directory scanning for a 10x performance improvement in `skill_fingerprint`.
## 2026-08-23 - Add lru_cache to _canonical_path and _canonical_key
**Learning:** Pure python path manipulation functions like `_canonical_path` and `_canonical_key` in `src/skill_manager/core/discovery.py` are heavily used during file discovery (which is O(N) over all skills). Caching them with `@lru_cache` provides a significant performance boost during startup and discovery updates, dropping time from ~5s down to ~0.02s for 100k calls.
**Action:** Always consider `@lru_cache` for pure python path manipulation functions like `normalize_path` or `canonical_path` that resolve string paths and are hit heavily during recursive operations like `os.scandir`.
