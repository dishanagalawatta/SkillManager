# QML Reference Errors Plan

## Approach
There are two reference errors causing UI breakdowns:
1. `PackageEditDialog.qml:165: ReferenceError: formScroll is not defined`. The `formPane` tries to access `formScroll.availableWidth` but the scroll view is named `contentScroll`.
2. `UpdatesView.qml: ReferenceError: updateAvailable is not defined`. The variables `isChecking`, `isUpdating`, `updateAvailable`, and `hasChecked` are defined on the `appUpdateBanner` rectangle, but they are used inside `Text` and `ActionButton` components without an ID prefix. In QML, scoping issues can cause these nested lookups to fail, resulting in reference errors. Prefixing these properties with `appUpdateBanner.` will fix the resolution issues.

## Scope
- In: `src/skill_manager/SkillManagerComponents/dialogs/PackageEditDialog.qml`, `src/skill_manager/SkillManagerComponents/views/UpdatesView.qml`.
- Out: Other components.

## Action Items
- [x] Task 1.1: Edit `PackageEditDialog.qml` to replace `formScroll.availableWidth` with `contentScroll.availableWidth`.
- [x] Task 1.2: Edit `UpdatesView.qml` to explicitly prefix all `isChecking`, `isUpdating`, `updateAvailable`, `latestVersion`, `currentVersion`, and `hasChecked` references inside `appUpdateBanner` with `appUpdateBanner.`.

## Validation
- The fixes are purely QML references, so they shouldn't break unit tests.
- We will rely on manual visual checks (or avoiding further log errors) since this is a runtime QML error.