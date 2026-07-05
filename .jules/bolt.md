## 2024-06-22 - rapidfuzz process.extractOne early-exit regression
**Learning:** `rapidfuzz.process.extractOne` evaluates the entire sequence to find the absolute maximum match. If the existing Python loop optimizes large list evaluations with an early exit (e.g. `if max_score > 70: break`), replacing it blindly with `extractOne` can actually cause performance regressions and functional differences.
**Action:** Always verify if the original looping logic relies on early termination thresholds. If it does, and the list size is significant, avoid `extractOne` and instead optimize the Python loop using fast-path exact substring checks before invoking expensive `fuzz.ratio` operations.

## 2026-07-05 - Add lru_cache to normalize_path
**Learning:** Applying `@lru_cache` to pure-Python path normalization functions (like `normalize_path`) is a highly effective micro-optimization for hot paths like file discovery. Using `extractOne` without understanding if the original logic relies on early termination can lead to performance regressions, as `extractOne` evaluates the whole sequence.
**Action:** Always check if a loop relies on an early-exit threshold before replacing it with `extractOne`. For functions strictly transforming strings/paths without I/O, apply `lru_cache` to prevent redundant work.
