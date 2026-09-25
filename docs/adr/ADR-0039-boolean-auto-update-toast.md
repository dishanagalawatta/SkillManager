# ADR-0039: Boolean Auto Update with Toast Notifications

> Status: **Accepted**
> Date: 2026-09-25
> Owner: @DIKKA

## Context

Skill package auto-update used a tri-state string setting (`off` / `prompt` / `silent`). Users found three modes confusing, and `prompt` had no visible surface beyond a status line. The request simplifies to on/off with explicit bottom-right popup notifications: off notifies with an Update action, on applies in the background and confirms completion.

## Decision

- Replace `skill_package_auto_update_mode: str` with `skill_package_auto_update: bool` (default off). Legacy configs migrate in `AppConfig.from_legacy` (`silent` → on, everything else → off); the old key is dropped.
- Update checks always run (startup scan + 6h `QtScheduler` job) regardless of the toggle.
- Auto Update **on**: outdated packages install in the background via `updateNow()`; completion emits `autoUpdateFinished`, shown as an informational `UpdateToast` popup.
- Auto Update **off**: outdated packages emit `updatesAvailable`, shown as an `UpdateToast` popup with an Update button that navigates to the Updates view and starts Update All.
- New `UpdateToast.qml` component hosted in `Main.qml` (bottom-right, above the status pill, 10s auto-dismiss). No OS desktop notifications — in-app only.
- The header count / Update All button continue to track outdated packages 1:1 (ADR scope: presentation parity established earlier).

## Consequences

### Positive

- One binary setting instead of three modes; every state has a visible, actionable surface.
- Off state still protects users via startup + periodic checks with one-click remediation.
- Toast signals are unit-testable (`updatesAvailable`, `autoUpdateFinished`); no OS notification permissions or D-Bus dependency.

### Negative

- Users on old `prompt` (the previous default) move to off: they now get a popup instead of a status line — slightly more intrusive, but actionable.
- A toast shown while the window is minimized may be missed until focus returns (no queue; latest signal wins on re-show).

### Neutral

- App self-updates (`AppUpdateController`, GitHub Releases) are untouched — separate feature.

## Alternatives Considered

### Keep tri-state and add toasts to prompt/silent

Rejected: preserves the confusing three-way model the request explicitly removes; more branches to test and document.

### OS desktop notifications instead of in-app toast

Rejected: requires notification permissions/daemons per platform, untestable in offscreen CI, and inconsistent with the existing in-app `statusToast` pattern.

## References

- `src/skill_manager/SkillManagerComponents/UpdateToast.qml`
- `src/skill_manager/controllers/update_controller.py` (`updatesAvailable`, `autoUpdateFinished`)
- Toast UI guidance: transient, non-blocking, auto-dismissing notifications
