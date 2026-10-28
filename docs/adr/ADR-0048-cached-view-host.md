# ADR-0048: Cached View Host

> Status: **Accepted**
> Date: 2026-10-28
> Owner: @DIKKA

## Context

`Main.qml` drove navigation with a single `Loader` whose `source` was bound to
`"views/" + window.currentView + "View.qml"`. Changing the `source` **destroys**
the previous item and **constructs** the next one from scratch. `QuickCopyView`
is ~1000 lines of QML with a `ListView` of `SkillItem` delegates, so every
switch back to Workbench rebuilt the whole tree on the GUI thread.

Measured on a 3-project / 360-skill workspace (`scripts/profile_ui_perf.py`,
frame-burst settle time):

| action | before | after |
|--------|-------:|------:|
| Workbench (return visit) | 484 ms, 14 frames, 22 ms worst frame | 62–106 ms, 2–3 frames |
| Hub (return visit) | 317 ms | 68 ms |
| Library (return visit) | 104 ms | 71 ms |

Half a second of jank on the most-used switch is the "app feels slow" report.

The rebuild is pure reconstruction cost, not data work: the same view loaded
warm (models already computed) was just as slow as the first load.

## Decision

Replace the single `Loader` with a **view host** that owns one `Loader` per
view (`QuickCopy`, `Library`, `Updates`, `Settings`), creates each on its first
visit, and afterwards switches by toggling `visible`.

- `viewLoader.show(view)` loads the target on first visit (`status ===
  Loader.Null`), calls the view's `activate()` when it is already alive, and
  hides every other loader.
- Leaving a view still runs `cleanup()`, which detaches the list model (and
  clears `cacheBuffer` first, per the incubation contract in ADR-0027). This
  keeps idle views from holding delegate memory and from reacting to model
  resets while hidden.
- `activate()` is the symmetric hook that re-attaches the models a view needs
  (`QuickCopyView`, `LibraryView`, `UpdatesView`); `SettingsView` needs none.
  `cleanup()`/`activate()` replace the implicit "construct = attach" behaviour
  the destroy-on-switch model relied on.
- `viewLoader.item` still means "the item of the view being shown", so
  `focusCurrentSearch()`, `scrollToTop` and `onClosing` needed no changes, and
  `isShowing(view)` replaces the old
  `viewLoader.source.toString().indexOf(...)` checks.

## Consequences

### Positive

- Returning to an already-visited view costs 2–3 frames instead of 14–17, and
  scroll position, filters and panel state survive the round trip.
- Navigation logic is state-based (`currentView` + `isShowing`), no longer a
  string comparison against a `source` URL.

### Negative

- Up to four view trees are alive at once. Models are detached while hidden, so
  the retained cost is the QML item tree, not delegates.
- Every view must implement `activate()` if it detaches models in `cleanup()`;
  a view that forgets it renders an empty list until the next model change.
  `tests/qml/test_qml_view_cache_contract.py` pins that pairing.
- The `Category:` top-bar path now routes through `navigateTo("QuickCopy")`
  instead of assigning a source directly, so `currentView` (and therefore the
  top-bar highlight) stays truthful.

### Neutral

- First visit to each view is still synchronous and still costs the full
  construction (~0.5 s for `QuickCopyView`). That cost is now paid once, on
  startup, instead of on every revisit.

## Alternatives Considered

### `Loader.asynchronous: true`

Rejected: it moves construction off the GUI thread but leaves the content area
blank for the same duration, then binds on the main thread. The user waits the
same time and sees less.

### `StackLayout` with all four views instantiated at boot

Rejected: pays all four construction costs before the window is usable. The
host creates views lazily, which keeps startup unchanged.

### Pre-destroy views after an idle timeout

Rejected as unnecessary complexity: `cleanup()` already drops the expensive
part (models/delegates) on switch; a timer would only trade memory for a
re-introduced rebuild spike.

## References

- `src/skill_manager/SkillManagerComponents/Main.qml` — `viewLoader` host
- `src/skill_manager/SkillManagerComponents/views/QuickCopyView.qml` — `activate()`
- `scripts/profile_ui_perf.py` — the measurement harness
- [ADR-0027](ADR-0027-path-self-healing-and-two-phase-incubation.md) — incubation / `cacheBuffer` contract
- `docs/ARCHITECTURE.md` — View Navigation
