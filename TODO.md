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

* **Compact list rows are the permanent default** — the "Normal" row mode, its
  Settings toggle and the `compact_list_rows` config key are gone. The row
  metrics live in the `Theme.row*` tokens. (`feat(ui): make compact list rows
  the permanent default`)
* **Unified custom command workflow** — the Library owns the canonical
  command; the create/edit dialog has no project selector, and deployment goes
  through the Library's copy flow, which asks before replacing an existing
  project command. (`feat(commands): unify the custom command
  create/edit/deploy workflow`)
* **Per-project task list** — a collapsible panel in Quick Copy holds the task
  list of the active project, with a quick-add field, priorities, filters and
  a "copy for agent" action. (`feat(tasks): add a per-project task list to
  Quick Copy`)
* **Packages view with a curated catalog** — "Updates" is now "Packages" (the
  view key stays "Updates"), with Installed / Discover / Project Sync tabs
  and a curated catalog of ready-to-install skill collections.
  (`feat(packages): add a curated catalog and rename Updates to Packages`)

### To Do (Ready for Pickup)

> Nothing queued right now — add the next task here.

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
