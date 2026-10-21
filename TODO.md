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

* [x] Update readme FI — added a Feature Index with working jump links, documented the Updates/auto-sync, MCP bridge, and accessibility capabilities, refreshed the "Why" table, removed the duplicated MCP developer blurb, fixed the stale docs-hub version and the "left sidebar" claim.
* [x] PostHog implementation review — found and fixed duplicated `mcp_tool_call` events (the server wrapper and every tool handler both captured, so live counts were ~2×; historical data confirms identical pairs one second apart). One emission point now attaches `ok`, `duration_ms`, and handler-contributed allowlisted properties; GeoIP is pinned off. Live MCP run: exactly one event per tool call.
* [x] Reduce the size of list row(normal mode) — 46 px → 40 px, icon 28 px, title 13 px (`SkillItem.qml` row metrics).
* [x] Release v2.13.2 — window-state restore, one `mcp_tool_call` per invocation, background MCP captures, tighter list rows, README feature index, and docs/ADR link fixes. Release PR #17, tag pushed; `.deb`, AppImage, and Windows Setup published.
* [x] Release v2.13.3 — accessibility names for inspector fields and hidden decorative chevrons (audit 6 → 0 across all four views), plus the release-script git-identity preflight. Release PR #22, tag pushed; `.deb`, AppImage, and Windows Setup published.
* [ ] Install v2.13.3 on the workstation (`bash scripts/install.sh --update`) — currently on v2.13.2; this release only changes accessibility metadata.

### In Progress

---

## 4. Bug Tracker

* [x] remember window position — root cause: on GNOME Wayland the compositor owns top-level placement, Qt ignores `setX`/`setY` and every window reports (0, 0). The app no longer overwrites the stored position there (it stays valid for X11/Windows sessions), and it now remembers the maximized state across restarts, which is client-controlled and works on Wayland.

---

## 5. Icebox / Backlog

### Windows code signing — free OSS route (SignPath Foundation)

* [ ] Submit application at <https://signpath.org/apply> — repo URL, Releases page, short description. Prerequisites are already in place: EXE `ProductName`/`ProductVersion` metadata and the README code signing policy.
* [ ] After approval: create the organization / project / signing-policy / artifact-configuration on signpath.io, add the `SIGNPATH_API_TOKEN` secret, then apply the workflow diff in [`docs/RELEASING.md`](docs/RELEASING.md).
* [ ] On Windows: align `installer.iss` `MyAppPublisher` so Add/Remove Programs matches the Authenticode publisher (SignPath Foundation). Needs a Windows machine — Inno Setup cannot be compiled on Linux.

### Leaked code-signing key (`packaging/windows/certs/code-signing.pfx`)

* [x] Removed on 2026-10-19 by deleting and recreating the repository. A rewrite alone could not: 138 `refs/pull/*` refs served the blob and cannot be rewritten by pushing. See `docs/SECURITY.md` for the measurement and the cost paid.
* [ ] Rotate/revoke the superseded certificate once a replacement is in use — revocation is what actually retires the key.

