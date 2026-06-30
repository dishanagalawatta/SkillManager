# Auto Update Feature

## Goal
Provide a seamless, secure, and configurable auto-update experience for SkillManager users.

## Requirements
- Use `tufup` for secure updates.
- Host TUF metadata on GitHub Pages (`gh-pages` branch).
- Support settings for:
  - Check on startup (boolean)
  - Periodic checks (boolean/interval)
  - Auto-download toggle (boolean)

## Architecture
- `AppUpdateController` acts as the `tufup` client wrapper.
- Settings are bound to UI via `ConfigController`.
- A new build script handles the `tufup` repository generation and pushes to the `gh-pages` branch during release.