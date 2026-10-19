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

### To Do (Ready for Pickup)

* [ ] Update readme FI
* [ ] PostHog implementation review.
* [ ] Reduce the size of list row(normal mode)

### In Progress

---

## 4. Bug Tracker

* [ ] remember window position - tried to bug. need further investigations (Not urgent)

---

## 5. Icebox / Backlog

### Windows code signing — free OSS route (SignPath Foundation)

* [ ] Submit application at <https://signpath.org/apply> — repo URL, Releases page, short description. Prerequisites are already in place: EXE `ProductName`/`ProductVersion` metadata and the README code signing policy.
* [ ] After approval: create the organization / project / signing-policy / artifact-configuration on signpath.io, add the `SIGNPATH_API_TOKEN` secret, then apply the workflow diff in [`docs/RELEASING.md`](docs/RELEASING.md).
* [ ] On Windows: align `installer.iss` `MyAppPublisher` so Add/Remove Programs matches the Authenticode publisher (SignPath Foundation). Needs a Windows machine — Inno Setup cannot be compiled on Linux.

### Leaked code-signing key (`packaging/windows/certs/code-signing.pfx`)

* [x] Removed on 2026-10-19 by deleting and recreating the repository. A rewrite alone could not: 138 `refs/pull/*` refs served the blob and cannot be rewritten by pushing. See `docs/SECURITY.md` for the measurement and the cost paid.
* [ ] Rotate/revoke the superseded certificate once a replacement is in use — revocation is what actually retires the key.

