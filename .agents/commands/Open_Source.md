---
name: Open Source
category: Custom Commands
type: command
date: 2026-07-03
---

Architecture Constraints: 
Do not build this feature or underlying system from the ground up if a high-quality, open-source framework, tool, or library exists that simplifies development and improves robustness. 

If introducing a new dependency (tool, framework, or library), it must meet the following criteria:
1. Actively maintained with recent updates.
2. Widely adopted with strong community support.
3. Well-documented with clear integration examples.
4. Fits naturally within the existing project ecosystem.
5. Permissive, production-friendly licensing (e.g., MIT, Apache 2.0).

Output Format: 
If a new dependency is selected, briefly justify the choice against the criteria above before providing the implementation code or configuration.