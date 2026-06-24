## 2024-06-22 - rapidfuzz process.extractOne early-exit regression
**Learning:** `rapidfuzz.process.extractOne` evaluates the entire sequence to find the absolute maximum match. If the existing Python loop optimizes large list evaluations with an early exit (e.g. `if max_score > 70: break`), replacing it blindly with `extractOne` can actually cause performance regressions and functional differences.
**Action:** Always verify if the original looping logic relies on early termination thresholds. If it does, and the list size is significant, avoid `extractOne` and instead optimize the Python loop using fast-path exact substring checks before invoking expensive `fuzz.ratio` operations.

## 2024-05-18 - Optimized rapidfuzz search with extractOne
**Learning:** In performance-sensitive search routines, nested Python loops calling C-extensions like `rapidfuzz` (e.g., `fuzz.ratio`) introduce massive overhead. RapidFuzz is optimized when processing lists natively in C++.
**Action:** When evaluating multiple fuzzy matches over an array, replace manual iterations with `rapidfuzz.process.extractOne(..., scorer=fuzz.ratio, score_cutoff=...)`. Always pass the targets as a `list` to maximize the C extension's performance.
