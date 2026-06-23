## 2024-06-22 - rapidfuzz process.extractOne early-exit regression
**Learning:** `rapidfuzz.process.extractOne` evaluates the entire sequence to find the absolute maximum match. If the existing Python loop optimizes large list evaluations with an early exit (e.g. `if max_score > 70: break`), replacing it blindly with `extractOne` can actually cause performance regressions and functional differences.
**Action:** Always verify if the original looping logic relies on early termination thresholds. If it does, and the list size is significant, avoid `extractOne` and instead optimize the Python loop using fast-path exact substring checks before invoking expensive `fuzz.ratio` operations.

## 2024-06-23 - rapidfuzz dictionary passing performance hit
**Learning:** When passing a collection of choices to `rapidfuzz.process.extractOne` in performance-critical paths, always pass a list (e.g., `list(dict.fromkeys(tokens))`) rather than a dictionary (e.g., `dict.fromkeys(tokens)`). The underlying C extensions optimize list processing significantly better than dictionary key iteration, leading to substantial speedups.
**Action:** Ensure collections passed to `extractOne` are strictly lists, converting deduplicated dictionaries back to lists before invoking the function.
