---
name: Open Source
category: Custom Commands
type: command
date: 2026-08-02
---

### Open-Source Library & Tooling Policy

**Core Directive:** 
When implementing, updating, or refactoring features, do not reinvent the wheel. You must prioritize using established, high-quality open-source libraries, frameworks, and packages over building custom solutions from the ground up to ensure code quality, accuracy, consistency, and professionalism.

**Anti-Hallucination & Tooling Mandate:**
- NEVER rely on your internal memory for library selection, versioning, syntax, capabilities, or known bugs. Your training data is likely outdated.
- You MUST utilize web search, context-retrieval, or external tools to research the current ecosystem of available tools before proposing or writing implementation code.

**Library Evaluation Criteria:**
Before integrating any third-party library, verify it meets the following standards via active external search:
1. **Active Maintenance:** Evidence of recent commits, active issue triage, and regular stable releases.
2. **Community Adoption:** High usage metrics (e.g., strong GitHub presence, active forks, high download counts on package managers like npm, PyPI, Maven, etc.).
3. **Quality & Professionalism:** Comprehensive, up-to-date official documentation and established best practices.
4. **Current Context:** Confirm the exact latest stable version, modern feature sets, and check for any currently critical open bugs, security vulnerabilities, or deprecation warnings.

**Execution Constraints:**
1. **Search First:** Actively search for existing libraries that solve the current requirements.
2. **Evaluate:** Cross-reference candidates against the evaluation criteria using your search tools.
3. **Implement:** Integrate the optimal library using its latest documented syntax and patterns.