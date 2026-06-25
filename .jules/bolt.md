## 2024-06-22 - rapidfuzz process.extractOne early-exit regression
**Learning:** `rapidfuzz.process.extractOne` evaluates the entire sequence to find the absolute maximum match. If the existing Python loop optimizes large list evaluations with an early exit (e.g. `if max_score > 70: break`), replacing it blindly with `extractOne` can actually cause performance regressions and functional differences.
**Action:** Always verify if the original looping logic relies on early termination thresholds. If it does, and the list size is significant, avoid `extractOne` and instead optimize the Python loop using fast-path exact substring checks before invoking expensive `fuzz.ratio` operations.

## 2024-XX-XX - Pre-compute unique tokens during indexing
**Learning:** In search engine or loop-heavy algorithms, operations like dynamic O(N) list-to-set conversions or unique dict-key conversions inside the per-document scoring loop add significant redundant overhead.
**Action:** Always pre-compute aggregated, deduplicated token lists (e.g., `all_doc_tokens = list(dict.fromkeys(...))`) during the indexing phase rather than dynamically constructing or deduplicating them inside the querying/scoring loops to optimize hot paths.
