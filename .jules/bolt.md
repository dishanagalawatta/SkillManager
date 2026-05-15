## 2025-05-15 - [Optimize Filter List Comprehensions]
**Learning:** Python list comprehensions are fast individually, but chaining multiple list comprehensions for complex filtering means iterating over the entire dataset multiple times. For an app holding potentially thousands of skills in memory and filtering on every UI interaction, this causes noticeable UI stutter.
**Action:** Replace chained list comprehensions with a single pass loop whenever filtering large in-memory collections based on multiple independent UI toggles.
