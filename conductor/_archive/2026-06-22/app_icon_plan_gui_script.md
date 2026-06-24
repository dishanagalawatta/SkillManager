# Systematic Debugging Plan: Fix 'uv run' AppUserModelID Issue

> Historical debug record — preserved for traceability. See
> [`conductor/tracks.md`](tracks.md) for the active track record.

**Status:** Historical (completed) · **Date:** unknown

## Symptom

Running `uv run skill-manager` results in a taskbar icon that is either completely blank or uses the default generic executable icon.

## Investigation

- **Root Cause A (Null Icon)**: Previous change switched the code to use `assets/brand/logo.ico`. While `.ico` is the native Windows format for embedded icons, PySide6/Qt requires the `qico` image format plugin to load them. If this plugin is missing in the local environment, `QIcon` fails silently. When `QIcon` is null and a custom `AppUserModelID` is active, Windows has no runtime icon to fall back on, resulting in a blank icon.
- **Root Cause B (Console Wrapper)**: `pyproject.toml` defines `skill-manager` under `[project.scripts]`. This causes `uv` to generate a *console* subsystem executable wrapper. Console host processes (`conhost.exe`) often interfere with taskbar grouping properties of GUI windows.

## Hypothesis

- Reverting to `assets/brand/logo.png` will ensure `QIcon` successfully loads (as PNG support is built-in). Qt automatically handles converting the PNG to the native Windows `HICON` format for the taskbar.
- Switching to `[project.gui-scripts]` in `pyproject.toml` will instruct `uv` to generate a *GUI* subsystem executable. This eliminates console-host interference and provides a cleaner process identity for the Windows shell.

## Resolution

1. **`src/skill_manager/app.py`**: Revert the icon resolution to strictly use `assets/brand/logo.png`.
2. **`pyproject.toml`**: Move the `skill-manager` entry point from `[project.scripts]` to `[project.gui-scripts]`.
3. **Verification**: Run `uv run skill-manager` and verify the custom icon appears correctly in the taskbar.

## Cross-references

- Workflow: [`conductor/workflow.md`](workflow.md)
- Active tracks: [`conductor/tracks.md`](tracks.md)
- ADRs: [`../ADR_INDEX.md`](../ADR_INDEX.md)
