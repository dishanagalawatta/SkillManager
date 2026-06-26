## 2024-06-22 - rapidfuzz process.extractOne early-exit regression
**Learning:** `rapidfuzz.process.extractOne` evaluates the entire sequence to find the absolute maximum match. If the existing Python loop optimizes large list evaluations with an early exit (e.g. `if max_score > 70: break`), replacing it blindly with `extractOne` can actually cause performance regressions and functional differences.
**Action:** Always verify if the original looping logic relies on early termination thresholds. If it does, and the list size is significant, avoid `extractOne` and instead optimize the Python loop using fast-path exact substring checks before invoking expensive `fuzz.ratio` operations.

## $(date +%Y-%m-%d) - Optimize RapidFuzz loops
**Learning:** In highly iterated `fuzz.ratio` loops checking across an array of tokens, replacing pure python nested iteration with `rapidfuzz.process.extractOne(query_token, tokens_list, scorer=fuzz.ratio, score_cutoff=current_max_score)` delegates the extraction evaluation to C++ backend pruning, providing substantial performance improvements on hot-paths in the python search engine logic without losing evaluation correctness.
**Action:** When finding fuzzy search or matching manual loops in python, replace them with `rapidfuzz.process` module alternatives appropriately matching the requirement while tracking dynamic cutoffs correctly.
