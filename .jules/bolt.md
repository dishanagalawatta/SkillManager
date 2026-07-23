## 2024-06-22 - rapidfuzz process.extractOne early-exit regression
**Learning:** `rapidfuzz.process.extractOne` evaluates the entire sequence to find the absolute maximum match. If the existing Python loop optimizes large list evaluations with an early exit (e.g. `if max_score > 70: break`), replacing it blindly with `extractOne` can actually cause performance regressions and functional differences.
**Action:** Always verify if the original looping logic relies on early termination thresholds. If it does, and the list size is significant, avoid `extractOne` and instead optimize the Python loop using fast-path exact substring checks before invoking expensive `fuzz.ratio` operations.
## 2026-07-10 - Fast-path exact match with list membership
**Learning:** Checking `if qt in all_doc_tokens:` where `all_doc_tokens` is a list of pre-computed string tokens acts as a fast, exact match check evaluated in C, whereas `qt in string` is a substring check. This is an optimal, fully isolated fast-path prior to executing expensive `fuzz.ratio` loops that rely on early-exit thresholds.
**Action:** When replacing loops that require early termination (`max_score > 70: break`), use list membership (`qt in list`) to short-circuit exact matches in a preliminary loop before executing the nested `fuzz.ratio` loops.
## 2026-07-23 - LRU Cache for Path Utilities\n**Learning:** Path manipulation in QML bridging (, ) causes large overheads during startup discovery. Using pure pathlib properties without I/O is safe for .\n**Action:** Use  heavily on pure path manipulation logic called during file walks.
## 2026-07-23 - LRU Cache for Path Utilities
**Learning:** Path manipulation in bridging (`skill_base_relative`, `project_root_for_project`) causes large overheads during startup discovery. Using pure pathlib properties without I/O is safe for `lru_cache`.
**Action:** Use `@lru_cache` heavily on pure path manipulation logic called during file walks.
