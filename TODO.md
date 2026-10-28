# 1. Project Metadata

* **Project Name:** CourseBar
* **Important Links:**
  * [Code Repository](https://github.com/dishanagalawatta/SkillManager)
  * [README](README.md)
  * [DESIGN](DESIGN.md)
  * [Environment](docs/ENVIRONMENT.md)
  * [Development](docs/DEVELOPMENT.md)
  * [ARCHITECTURE](docs/ARCHITECTURE.md)
  * [API](docs/API.md)
  * [VERSIONING](docs/VERSIONING.md)

---

## 2. High-Level Milestones

* **Goal A:**
* **Goal B:**

---

## 3. Active Task Tracker

### Done

* [X] Drop the unnecessary outer circle around the close circular button — `eb333a6`
* [X] Top bar client selector defaults to two entries, with Settings able to add up to two more (max four) — `ebee87b`
* [X] Move Installed / Discover / Project Sync into a bar above the panel, with the actions in that bar swapping to match the active tab — `ebee87b`
* [X] Snap is now an icon button next to Refresh; "Quick Copy" renamed to **Workbench** and "Packages" to **Hub** — `ebee87b`
* [X] Collapsing all then expanding one category no longer expands its parent categories — `e915f5d`
* [X] Commands share one common icon instead of the category icon — `f298dde`
* [X] Adding an existing command from the Library no longer errors (asks before reusing the name) — `48c4146`
* [X] Tasks are written inline in the task list box: multi-line notes, bullet/sub-task continuation, image paste/drop, priority pill, per-project drafts, `Ctrl+Enter` to add — `715a8e1`
* [X] UI snappiness: views are created once and kept alive (`cleanup()`/`activate()`), task state read through an inode/mtime cache — Workbench return 484 ms → 62–106 ms, Hub 317 ms → 68 ms, `get_tasks` 1.29 ms → 0.042 ms — `d6a90d5`
* [X] `portal_hotkeys.py` no longer burns CPU in the background — `5cdc0eb`

### To Do (Ready for Pickup)

### In Progress

---

## 4. Bug Tracker

---

## 5. Icebox / Backlog

### Windows code signing — free OSS route (SignPath Foundation)

* [ ] Submit application at [https://signpath.org/apply](https://signpath.org/apply) — repo URL, Releases page, short description. Prerequisites are already in place: EXE `ProductName`/`ProductVersion` metadata and the README code signing policy.
* [ ] After approval: create the organization / project / signing-policy / artifact-configuration on signpath.io, add the `SIGNPATH_API_TOKEN` secret, then apply the workflow diff in [`docs/RELEASING.md`](docs/RELEASING.md).
* [ ] On Windows: align `installer.iss` `MyAppPublisher` so Add/Remove Programs matches the Authenticode publisher (SignPath Foundation). Needs a Windows machine — Inno Setup cannot be compiled on Linux.

### Leaked code-signing key (`packaging/windows/certs/code-signing.pfx`)

* [X] Removed on 2026-10-19 by deleting and recreating the repository. A rewrite alone could not: 138 `refs/pull/*` refs served the blob and cannot be rewritten by pushing. See `docs/SECURITY.md` for the measurement and the cost paid.
* [ ] Rotate/revoke the superseded certificate once a replacement is in use — revocation is what actually retires the key.
