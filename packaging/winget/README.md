# winget manifests

Manifests for publishing SkillManager to the
[Windows Package Manager community repository](https://github.com/microsoft/winget-pkgs)
— the default source behind `winget install`.

## Layout

`manifests/<letter>/<Publisher>/<PackageName>/<Version>/` mirrors winget-pkgs exactly:

| File | `ManifestType` |
|---|---|
| `dishanagalawatta.SkillManager.yaml` | `version` |
| `dishanagalawatta.SkillManager.installer.yaml` | `installer` |
| `dishanagalawatta.SkillManager.locale.en-US.yaml` | `defaultLocale` |

## Status: NOT published

`winget install --id dishanagalawatta.SkillManager` fails with *"No package found
matching input criteria."* The original submission —
[microsoft/winget-pkgs#391299](https://github.com/microsoft/winget-pkgs/pull/391299)
(v1.8.0) — was closed **unmerged** as *Stale* on 2026-07-21. Its CLA check had passed
and no reviewer ever commented, so it simply timed out; re-submitting is the fix.

`1.7.0/` and `1.8.0/` are historical staging copies. **Only the newest version
folder is ever submitted** — winget-pkgs rejects a PR that adds older versions
alongside the current one.

## Submitting a version

1. Bump `MyAppVersion` in [`packaging/windows/installer.iss`](../windows/installer.iss),
   cut the release, and let `.github/workflows/release-build.yml` publish
   `SkillManager_Setup.exe`.
2. Copy the newest version folder to a new one named for the release (`2.13.0/`), then
   update, in all three files:
   - `PackageVersion`
   - `InstallerUrl` (the `vX.Y.Z` tag)
   - `InstallerSha256` — **uppercase** hash copied from the release's `SHA256SUMS`
   - `ReleaseDate` (`yyyy-MM-dd`) and `ReleaseNotesUrl`
3. Fork `microsoft/winget-pkgs` and add the **new version folder only** at
   `manifests/d/dishanagalawatta/SkillManager/<version>/`.
4. Open a PR. If the CLA bot asks, reply with the phrase
   `@microsoft-github-policy-service agree` on its own line.

Manifest versions are bumped as winget publishes new schemas (`1.28.0` at the time of
writing). Update the `ManifestVersion` field and the `$schema` comments together.

## What was verified for 2.12.1

- All three files validate against the official schemas
  (`https://aka.ms/winget-manifest.*.1.28.0.schema.json`).
- `ProductCode` equals the Inno Setup `AppId` in `installer.iss` (`{{5A1B8C9D-…}}_is1`).
- `InstallerSha256` equals the SHA-256 of the published `SkillManager_Setup.exe`
  (downloaded and hashed — not just copied from `SHA256SUMS`).
- `InstallerUrl` returns HTTP 200 with the expected byte length.
- `PackageVersion` matches the installer's `ProductVersion` resource and the release tag.

`winget validate` and the actual submission require Windows.
