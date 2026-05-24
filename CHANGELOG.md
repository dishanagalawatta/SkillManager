# CHANGELOG


## v0.1.0-dev.7 (2026-05-24)


## v0.1.0-dev.6 (2026-05-24)

### Bug Fixes

- Streamline artifact paths and enhance source zip packaging for platform specificity
  ([`9aa77fd`](https://github.com/dishanagalawatta/SkillManager/commit/9aa77fd26602f8f91b2cb28da59f53420f3b25c4))


## v0.1.0-dev.5 (2026-05-24)

### Bug Fixes

- Update release workflow to prevent early job termination and add macOS dependencies
  ([`ad3b457`](https://github.com/dishanagalawatta/SkillManager/commit/ad3b457d0efe22b8bd1af5a59df217c132ebaa40))


## v0.1.0-dev.4 (2026-05-24)

### Bug Fixes

- **ux**: Resolve missing string properties in a11y labels
  ([`b927545`](https://github.com/dishanagalawatta/SkillManager/commit/b92754585810d676f30be7421cdeeec4e4094d6d))

* Fixed `modelData.query` causing binding errors (or "undefined") by replacing it with just
  `modelData`. * Fixed `modelData.fileName` causing errors in SkillInspector. Replaced with
  `modelData.name`. * Fixed `root.skillName` causing errors in SkillItem. Replaced with
  `model.name`.

Co-authored-by: dishanagalawatta <113381719+dishanagalawatta@users.noreply.github.com>

- **ux**: Update a11y labels to point to correct property
  ([`fdecd54`](https://github.com/dishanagalawatta/SkillManager/commit/fdecd540e8bdc1fc1dfcf35219987c7fd135845f))

* `modelData` -> `modelData.label` in `LibraryView.qml` and `QuickCopyView.qml` to correctly reflect
  the history display chip text.

Co-authored-by: dishanagalawatta <113381719+dishanagalawatta@users.noreply.github.com>

### Features

- **ux**: Add missing Accessible properties to custom QML components
  ([`0764b5e`](https://github.com/dishanagalawatta/SkillManager/commit/0764b5e9c62a01375fc022e6d84f8223535be49f))

* Adds Accessible.role, Accessible.name, and Accessible.description properties to several
  interactive UI components, primarily those using MouseArea as the interactive layer without a
  native accessible role. * Improved screen reader support in CustomTitleBar, KeySequenceCapture,
  SkillItem, LibraryView, and QuickCopyView. * Updated UX journal with learnings regarding nested
  custom button implementations.

Co-authored-by: dishanagalawatta <113381719+dishanagalawatta@users.noreply.github.com>


## v0.1.0-dev.3 (2026-05-24)

### Bug Fixes

- Unify release workflow and update documentation
  ([`5e98d34`](https://github.com/dishanagalawatta/SkillManager/commit/5e98d349d7faa6f681108ce66aeefab030b5aa10))


## v0.1.0-dev.2 (2026-05-24)

### Bug Fixes

- Update skill-manager version to 0.1.0.dev1
  ([`0bb8bac`](https://github.com/dishanagalawatta/SkillManager/commit/0bb8bac718505da2d99847c64101a13087d4d2de))


## v0.1.0-dev.1 (2026-05-24)

### Bug Fixes

- Include .zip files in artifact upload for release
  ([`f065d66`](https://github.com/dishanagalawatta/SkillManager/commit/f065d66ce20a5440bb1477931f2e79f0051ad416))

- Migrate FolderDialog from Qt5 folder to Qt6 selectedFolder property
  ([`dc62b2d`](https://github.com/dishanagalawatta/SkillManager/commit/dc62b2d31e9fb9be0f720f08c77a2a24e27f9235))

- Parse quoted verify paths correctly in cross-platform command interceptor
  ([`5a1b4e7`](https://github.com/dishanagalawatta/SkillManager/commit/5a1b4e72fc1690e7707ee69e695ef180d92b9909))

- **quick-copy**: Use friendly projectLabels instead of full projects path in QuickCopyView project
  dropdown
  ([`6910f3d`](https://github.com/dishanagalawatta/SkillManager/commit/6910f3d5b3af091ab9d1f29eb63864e826317b11))

### Chores

- Fix Git case-sensitivity and line-ending conflicts for .jules directory
  ([`b82a05a`](https://github.com/dishanagalawatta/SkillManager/commit/b82a05ad227094d29c2191ce7cde1b47e36b8554))

Add .gitattributes to enforce LF for markdown files and consolidate .jules directory naming to
  lowercase to resolve Windows/Git case conflicts.

Co-Authored-By: Gemini CLI <noreply@google.com>

- Remove completed tasks from TODO list
  ([`1bf1ae6`](https://github.com/dishanagalawatta/SkillManager/commit/1bf1ae6f459d4fbca65b2a65828a5516d8245501))

- Remove unused import os in parsing.py
  ([`23545fa`](https://github.com/dishanagalawatta/SkillManager/commit/23545fab541b1e4b09247d21fdbe55a5fae1c5f0))

Co-authored-by: dishanagalawatta <113381719+dishanagalawatta@users.noreply.github.com>

- Update logo.ico asset
  ([`7cffd70`](https://github.com/dishanagalawatta/SkillManager/commit/7cffd709fe9ef951a2dcbdfb850589821aa52ec1))

- Update logo.ico asset
  ([`faae643`](https://github.com/dishanagalawatta/SkillManager/commit/faae643fe60cdc24d392f02efa7834946e525e16))

### Documentation

- Update
  ([`7f34f23`](https://github.com/dishanagalawatta/SkillManager/commit/7f34f23f2f6c5a992df37cb2bc18c2986a10f0fe))

- Update
  ([`e223d40`](https://github.com/dishanagalawatta/SkillManager/commit/e223d406b9c0cebde41ba216cbdd25d11d185e8c))

- Update accessibility guidelines for custom QML buttons
  ([`0c8df4c`](https://github.com/dishanagalawatta/SkillManager/commit/0c8df4cba0a5b59dda313f25a972bb34e2b3ec96))

- Update bolt.md with optimization details for categorize_skill regex and add new accessibility
  guidelines for custom QML controls in palette.md
  ([`45e464b`](https://github.com/dishanagalawatta/SkillManager/commit/45e464b9c76623f3173b09b4dccc2b0b61db33ce))

- Update TODO.md to include refactor for testable code
  ([`20a5f3f`](https://github.com/dishanagalawatta/SkillManager/commit/20a5f3f11a62628d2b9404102c418f9d0c4dd388))

### Features

- Add missing archive button to TODO list
  ([`5fc0020`](https://github.com/dishanagalawatta/SkillManager/commit/5fc00200d67c2d470d7cbb4ff387e38997af95e5))

- Enhance targetWidth calculation for SkillInspector component
  ([`0ae82cd`](https://github.com/dishanagalawatta/SkillManager/commit/0ae82cd64cc8ce6a1afd25cecd434623faa46ab1))

- Implement background update service, automated CI/CD release pipeline, and QML behavior validation
  tests
  ([`5755f51`](https://github.com/dishanagalawatta/SkillManager/commit/5755f5188811a910f09a09a02b53fe82173285fb))

- Implement core skill parsing engine and initial project structure with UI components and tests
  ([`99ae139`](https://github.com/dishanagalawatta/SkillManager/commit/99ae139d79c0c5e761a2fabd408a23e06a234f38))

- Implement initial project structure with QML-based UI, core backend logic, and test suite
  ([`236093e`](https://github.com/dishanagalawatta/SkillManager/commit/236093ebb5316b7a80cb124df7f6fa40dada05a6))

- Implement new UI components and asset support for SkillManager
  ([`e05291d`](https://github.com/dishanagalawatta/SkillManager/commit/e05291d1d98a05889ff6eccce9e449ec76d03d89))

- Implement SplitView for improved layout in LibraryView and QuickCopyView
  ([`54f4185`](https://github.com/dishanagalawatta/SkillManager/commit/54f4185614fe7cd0116ca7693561ae86a7f04892))

- Initialize configuration files in the .jules directory
  ([`be6893d`](https://github.com/dishanagalawatta/SkillManager/commit/be6893d8555e309d5fd9489e34a950b74a9da571))

- Initialize SkillManager project structure with core logic, QML UI components, and comprehensive
  test suite
  ([`2b36ba2`](https://github.com/dishanagalawatta/SkillManager/commit/2b36ba21a9e7a453167c6811d9c14f5b7719b986))

- Shortcuts support
  ([`607db28`](https://github.com/dishanagalawatta/SkillManager/commit/607db2826c6a49a434c7bdbc7e3cf92af5573b85))

- Standardise menu behavior and list item selection across views
  ([`663125f`](https://github.com/dishanagalawatta/SkillManager/commit/663125f57974faee3e7c73b2a0b89badd948173d))

- Version implementation
  ([`7537d43`](https://github.com/dishanagalawatta/SkillManager/commit/7537d43c9e83d31204ebfa06de92149bb9cc2b98))

### Performance Improvements

- Optimize `categorize_skill` regex and normalizations
  ([`e863f96`](https://github.com/dishanagalawatta/SkillManager/commit/e863f9637a063ffaf7db899a5e23e5041da9b28f))

- Convert plain keywords into a single non-capturing regex group `\b(?:word1|word2)\b` per category
  instead of individual regexes - Drop `re.I` and pre-lowercase keywords, and `text` string instead
  - Use a pre-compiled `_SEPARATOR_REGEX` for faster regex matching while maintaining exact behavior

Co-authored-by: dishanagalawatta <113381719+dishanagalawatta@users.noreply.github.com>

- Optimize `categorize_skill` regex and normalizations
  ([`3a2fb3b`](https://github.com/dishanagalawatta/SkillManager/commit/3a2fb3b50f426ea88c680d7775b686c0904a2202))

- Convert plain keywords into a single non-capturing regex group `\b(?:word1|word2)\b` per category
  instead of individual regexes - Drop `re.I` and pre-lowercase keywords, and `text` string instead
  - Swap `re.sub` string normalization for faster `str.replace`

Co-authored-by: dishanagalawatta <113381719+dishanagalawatta@users.noreply.github.com>

- Optimize skill sorting key generation
  ([`39f488e`](https://github.com/dishanagalawatta/SkillManager/commit/39f488e5d469eee8743ab8595e0fee4b8c0a6a3c))

Hoists static dictionary creation out of the sorting key function and uses early returns to speed up
  repetitive dictionary lookups during skill list filtering.

Co-authored-by: dishanagalawatta <113381719+dishanagalawatta@users.noreply.github.com>

- Optimize skill update scan nested loop
  ([`7fbc422`](https://github.com/dishanagalawatta/SkillManager/commit/7fbc4228f6cfb0e9c4246df982248c4f5d48688f))

Improved the performance of the skill update scan by pre-indexing target project skills into
  dictionaries. This replaces an O(N) lookup inside a nested loop with an O(1) dictionary lookup,
  significantly reducing the overall time complexity of the scan operation.

Key changes: - Pre-calculate `target_skill_maps` containing dictionaries of skills for each project.
  - Use dictionary `.get()` for O(1) skill lookup instead of `next()` with a generator expression.

Benchmark results on synthetic data (500 source skills, 20 projects): - Baseline: ~0.15s -
  Optimized: ~0.01s - Speedup: ~15x

Co-authored-by: dishanagalawatta <113381719+dishanagalawatta@users.noreply.github.com>

### Refactoring

- App for testable test cases
  ([`58ff477`](https://github.com/dishanagalawatta/SkillManager/commit/58ff477b6eb4140e16da13fb890e84b48a44716b))

- App for testable test cases
  ([`61a255f`](https://github.com/dishanagalawatta/SkillManager/commit/61a255f7080d8cb68027eed29c9fe55b0ccc5ff4))

- Clean up imports and whitespace in test files for consistency
  ([`1f2968c`](https://github.com/dishanagalawatta/SkillManager/commit/1f2968c7d7b3665ada219ddb654a474521a4db81))

- Refactored code base for testable units
  ([`565e584`](https://github.com/dishanagalawatta/SkillManager/commit/565e584fc360caf676923335e2ab9ded4182ad44))

- Remove unused imports across multiple files
  ([`ccecf24`](https://github.com/dishanagalawatta/SkillManager/commit/ccecf2490ac1828158a1d1d26e63fd9ff18cd4db))

- Update
  ([`19f976c`](https://github.com/dishanagalawatta/SkillManager/commit/19f976c355ccc72e02ae03fced73b7aa0f12d2f5))

- Update color properties to use alpha transparency for improved UI consistency
  ([`d1a9009`](https://github.com/dishanagalawatta/SkillManager/commit/d1a9009cf2f5e0183d412c564a48395c3c1c4f00))

- Update TopBarButton background structure and remove unused test file
  ([`e148243`](https://github.com/dishanagalawatta/SkillManager/commit/e148243661461f0f1c2713125cc368eff5e07fac))
