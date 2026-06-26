## 2024-06-22 - rapidfuzz process.extractOne early-exit regression
**Learning:** `rapidfuzz.process.extractOne` evaluates the entire sequence to find the absolute maximum match. If the existing Python loop optimizes large list evaluations with an early exit (e.g. `if max_score > 70: break`), replacing it blindly with `extractOne` can actually cause performance regressions and functional differences.
**Action:** Always verify if the original looping logic relies on early termination thresholds. If it does, and the list size is significant, avoid `extractOne` and instead optimize the Python loop using fast-path exact substring checks before invoking expensive `fuzz.ratio` operations.

## 2026-06-26 - Pre-compute indexing data
**Learning:** To optimize search engine performance, pre-compute aggregated and deduplicated token lists (e.g., `all_doc_tokens = list(dict.fromkeys(...))`) during the indexing phase rather than dynamically concatenating or deduplicating them inside the scoring loop.
**Action:** When finding fuzzy search or matching manual loops in python, always ensure pre-computations are handled when building the index mapping rather than during query scoring loops, as the O(N) conversion overhead causes significant performance regressions.
