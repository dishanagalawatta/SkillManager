# ADR-0024: Verified Dual-Write Clipboard Handling

> Status: **Accepted**
> Date: 2026-08-12
> Owner: @DIKKA

## Context

Qt's `QClipboard` can silently fail or drop selection ownership when a window is minimized or loses focus on Linux desktop environments (both Wayland and X11). The application's "Quick Copy" feature auto-minimizes upon copying skills, which previously triggered a race condition:
1. Under Wayland (`QWaylandClipboard`), Qt releases selection ownership when its window loses focus, destroying clipboard content before external target applications can paste it.
2. Writing strictly via `wl-copy` set the Wayland compositor selection, but left Qt's internal `QGuiApplication.clipboard()` unpopulated and out of sync for in-process or Xwayland components.
3. Probing for `wl-copy` relied solely on executable binary presence rather than active Wayland display connection validation, causing non-zero exit failures on X11 sessions.
4. CLI fallback tools for X11 (`xclip` / `xsel`) were missing from native helper routines.
5. In frozen binaries and AppImages, `LD_LIBRARY_PATH` points to bundled runtime libraries (`_internal`), causing external host CLI tools (`wl-copy`, `xclip`, `ydotool`) to fail due to dynamic linker symbol version mismatches.

## Decision

We adopt a **Verified Dual-Write Clipboard Strategy** via `ClipboardService` and platform helpers:

1. **Subprocess Environment Sanitization**: `linux.get_clean_env()` strips bundled `LD_LIBRARY_PATH` (or restores `LD_LIBRARY_PATH_ORIG`) when executing external host CLI binaries (`wl-copy`, `wl-paste`, `xclip`, `xsel`, `ydotool`, `wmctrl`, `xdotool`).
2. **Multi-Tier Binary Discovery**: `linux.find_system_binary()` probes standard Linux directories (`/usr/bin`, `/usr/local/bin`, `/snap/bin`, `~/.local/bin`) in addition to `PATH`.
3. **Active Session Probing**: `linux.is_wayland_active()` verifies `XDG_SESSION_TYPE`, `WAYLAND_DISPLAY`, and runtime directory sockets (`/run/user/<uid>/wayland-*`) before attempting `wl-copy` / `wl-paste`.
4. **Dual-Write Execution**: Whenever text is copied, `ClipboardService` populates both the native system selection daemon (`wl-copy` on Wayland, `xclip`/`xsel`/`pyperclip` on X11) **and** Qt's `QGuiApplication.clipboard()` (populating both `Clipboard` and `Selection` modes on Linux).
5. **Verified Readback**: Readback verification tests against the real system clipboard using native readers (`wl-paste`, `xclip`, `xsel`, `pyperclip`), using symmetric trailing-newline normalization (`.rstrip("\r\n")`).
6. **Service Unification**: All clipboard writes (including screen capture reference text in `SnapController`) route through `app.clipboard_service.copy_text()`.

## Consequences

### Positive

- **Persistence across minimize**: Native CLI tools (`wl-copy`, `xclip`, `xsel`, `pyperclip`) hold persistent selection ownership after `_maybeMinimizeOnCopy()` minimizes the window.
- **Packaged App Stability**: System tools execute cleanly in PyInstaller and AppImage environments without library conflict crashes.
- **In-process consistency**: Qt `QClipboard` remains in sync for internal UI views and QML components.
- **Robust X11 & Wayland support**: Seamless fallback across Wayland, X11, Windows, and headless testing environments.

### Negative

- Native clipboard readback verification incurs a small sub-millisecond delay (~50ms retry loop) when confirming system compositor selection state.

### Neutral

- Tests mocking `QGuiApplication.clipboard()` require `ClipboardService` type checks to ensure isolated test execution.

## Alternatives Considered

### Relying Solely on QClipboard

Rejected. Qt's `QWaylandClipboard` drops selection when window focus is lost on minimize.

### Relying Solely on Native Tools (`wl-copy` / `xclip`)

Rejected. Bypassing Qt leaves internal QML/Python clipboard readers out of sync.

## References

- [ClipboardService Source](file:///home/dikka/Documents/01-Projects/27-SkillManager/skill-manager/src/skill_manager/utils/clipboard_service.py)
- [Linux Utils Source](file:///home/dikka/Documents/01-Projects/27-SkillManager/skill-manager/src/skill_manager/utils/linux.py)
