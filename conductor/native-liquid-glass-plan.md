# Plan: Native Liquid Glass UI Update (Approach A)

Upgrade the Skill Manager UI to use native Windows 11 Mica and Windows 10 Acrylic effects. This approach leverages the Desktop Window Manager (DWM) to provide a true "Liquid Glass" look with system-level transparency and blur.

## Objective
- Achieve an immersive, vibrant, and translucent UI.
- Use native Windows materials (Mica/Acrylic) for the main window background.
- Refactor the app layout to a modern sidebar-driven shell.
- Ensure high-performance fallbacks for older systems or accessibility settings.

## Key Files & Context
- `src/skill_manager/app.py`: Root window, layout, and tab management.
- `src/skill_manager/gui/styles.py`: Theme tokens, color management, and style helpers.
- `src/skill_manager/gui/components.py`: Shared UI components (`GlassPill`, `SkillInspectorOverlay`).
- `src/skill_manager/utils/win32.py`: Native Windows utility functions.

## Implementation Steps

### Phase 1: Native Integration & Utilities
- [ ] Add `pywinstyles` to `pyproject.toml` dependencies.
- [ ] Update `src/skill_manager/utils/win32.py` to include `apply_native_style(window, style_name)` helper.
    - Implement version-safe `DwmSetWindowAttribute` calls for Mica (Win11) and Acrylic (Win10).
    - Handle HWND resolution correctly for Tkinter windows.

### Phase 2: Theme & Style Refinement
- [ ] Update `src/skill_manager/gui/styles.py`:
    - Define a `TRANSPARENT` or `VIBRANT` background token (usually `#000001` or `black` for DWM bleed).
    - Adjust `glass_bg` and `glass_bg_strong` opacities to better complement native materials.
    - Enhance `glass_border` (inner reflection) for higher contrast on blur.
- [ ] Refine `GlassPill` in `src/skill_manager/gui/components.py` to ensure it maintains a "floating" look on top of native materials.

### Phase 3: Shell Architecture Refactor
- [ ] In `src/skill_manager/app.py`:
    - Remove `self.tabview = ctk.CTkTabview(...)`.
    - Create a `SidebarFrame` (Layer 1: High-opacity frosted glass).
    - Create a `MainContentFrame` (Layer 0: Native material background).
    - Implement a navigation controller to swap views (Quick Copy, Library, Projects, Updates).
- [ ] Apply `pywinstyles.apply_style(self, "mica")` (or "acrylic") during initialization.

### Phase 4: View Migration (Pill-Stacked Model)
- [ ] **Library View**:
    - Re-implement as a split-pane view with Layer 2 glass pills.
    - Left pill: Category tree.
    - Right pill: persistent Skill Inspector.
- [ ] **Quick Copy View**:
    - Re-implement as a vertical stack of specialized glass pills (Context, Config, Essentials, Manuals, Tree).
- [ ] **Update View**:
    - Refine sequential layout with glass containers for Sources and Targets.

### Phase 5: Verification & Polish
- [ ] Test on Windows 11 to confirm Mica effect.
- [ ] Test on Windows 10 to confirm Acrylic effect.
- [ ] Verify "Reduced Transparency" mode correctly disables native effects and uses opaque fallbacks.
- [ ] Ensure `ttk.Treeview` and other legacy components remain readable on vibrant backgrounds.

## Verification
- [ ] **Visual**: The window should show desktop wallpaper blur behind the UI.
- [ ] **Functional**: All existing workflows (Copy, Library, Update) must remain operational.
- [ ] **Performance**: The app should remain responsive during window resizing and theme switching.
- [ ] **Accessibility**: Text contrast must meet WCAG AA on all glass surfaces.

## Open Questions
- Should we force a specific multi-tonal wallpaper as a fallback for systems without native blur?
- How does `tkinterdnd2` interact with a fully transparent/acrylic root window? (Need to verify drag/drop targets).
