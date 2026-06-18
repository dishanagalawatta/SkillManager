# Skill Manager - Solid Matte & Liquid Glass Design Guide

## Design Intent

Skill Manager follows a **Solid Matte** aesthetic inspired by high-end pro-developer tools. It balances the depth of Apple's Liquid Glass with the stability of solid, deeply-tinted materials. The interface prioritizes a "Modern Graphite" palette—using sleek neutral grays and blue accents—to create a premium, focused workspace. While functional components (pills) maintain frosted translucency, the main window background utilizes solid, non-transparent colors to ensure consistent visual fidelity across all OS configurations and display scales.

## Product Context

- **Name:** Skill Manager
- **Category:** Desktop productivity / developer utility
- **Current stack:** Python 3.12+, PySide6 (Qt 6.8+), QML, `uv`, `ruff`, `sentry-sdk`, `posthog`, `apscheduler`
- **Primary platforms:** Windows (Native Mica/Acrylic)
- **Design project:** Desktop software utilizing modern hardware acceleration via Qt 6.
- **Primary users:** Developers and power users managing local skill folders across multiple project repositories.

## Existing Workflows To Preserve

The Liquid Glass redesign must not move or weaken these workflows:

- **Quick Copy:** Browse skills discovered in project paths, select/copy references, manage saved sets, handle command references, and keep project-scoped state clear.
- **Library:** Browse local skills, search, filter by category, expand/collapse categories, select multiple skills, archive/unarchive, open skill details, and copy selected skill folders to configured project projects.
- **Copy to Projects:** Keep this action in the Library workflow. It supports multi-select and copies whole skill folders, not only `SKILL.md`.
- **Updates:** Manage source and project project directories, drag/drop paths, reorder sources, run folder updates, manage configured skill update commands, run update checks, and sync linked project projects after successful source updates.
- **Starred and commands:** Treat Starred and command references as first-class selectable items wherever the Quick Copy workflow shows project skills.

## Solid Matte & Glass Principles

The redesign treats the UI as a series of high-contrast, rounded containers floating over a stable, solid base:

- **Solid Matte Foundation:** The primary window utilizes a solid, deeply-tinted material (e.g., `#121214` in Dark Mode) instead of full-window transparency. This provides a robust, professional feel and eliminates "glowing" or "leaking" artifacts from the desktop wallpaper.
- **Glass-Pill Components:** Functional sections (toolbars, sidebars) and content areas remain encapsulated in "frosted glass" pills. These pills use subtle alpha-blending or distinct tinting (`#1E1E22`) to stand out against the matte background.
- **Synchronized Rounding:** All primary containers and the main window frame use a **12px corner radius**. This value is strictly synchronized with the Windows 11 native DWM corner preference (`DWMWCP_ROUND`) to ensure perfectly aligned shadows and borders.
- **Inner Reflection Borders:** Components use 1px solid tinted borders (`#2A2A30`) to define edges. These act as "reflection" points that give the UI a layered, physical presence without relying on heavy gradients.
- **Premium Micro-Animations:** Interaction is enhanced with subtle 150ms transitions on hover and focus states, making the matte surfaces feel "alive" and responsive.

## HIG Principles Applied

The redesign should continue to follow these Apple HIG-derived principles:

- **Hierarchy:** controls and navigation should elevate above content without obscuring it.
- **Harmony:** shapes, corner radii, spacing, symbols, and transitions should feel consistent across the shell, toolbar, lists, dialogs, and popovers.
- **Consistency:** commands should stay in predictable places and behave the same across Quick Copy, Library, Projects, and Updates.
- **Content over chrome:** reduce decorative surfaces, heavy outlines, large brand treatments, saturated gradients, and oversized headers.
- **System feeling first:** use neutral surfaces, subtle separators, platform fonts, predictable controls, and restrained accent color.
- **Clear current state:** selections, active filters, running jobs, disabled controls, and copy/update results must always be visible.
- **Minimize modality:** use inline status, progress, popovers, toasts, and undo-style recovery where practical. Reserve modal dialogs for focused setup or destructive confirmation.
- **Progressive disclosure:** show primary actions first, move advanced or lower-frequency actions into overflow menus, disclosure sections, or contextual panels.
- **Keyboard and pointer productivity:** common commands should support shortcuts, focus order, right-click context menus, visible hover/selection states, and double-click/Enter activation.
- **Accessibility from the start:** labels, contrast, focus visibility, reduced-motion behavior, resizable text, and screen-reader-friendly state text are design requirements.

## Visual Direction

### Overall Feel

Use a Liquid Glass desktop utility aesthetic: light by default, excellent dark-mode support, compact spacing, crisp typography, soft hierarchy, and functional glass surfaces that appear to float above stable content.

Avoid dashboard-heavy cards, saturated gradients, glowing brand surfaces, one-note color palettes, oversized hero-style headers, and decorative glass panels. Skill Manager is a work tool; the glass treatment should make navigation and controls feel modern while letting users scan rows quickly.

### Window Structure

Recommended root layout:

```text
Window
  Functional glass layer
    Title/toolbar area
      App title
      Primary toolbar actions
      Search where relevant
    Sidebar or top-level navigation
    Floating/status feedback
  Content layer
    Main split layout
      Source/list region
      Content/detail region
      Optional inspector/detail panel
  Bottom status area
    Progress, result summary, transient messages
```

The app uses a sidebar-driven layout (implemented in QML `Sidebar.qml`), which replaced the previous tab-based navigation:

| Sidebar Item | Purpose |
|---|---|
| Quick Copy | Project reference copying |
| Library | Local skill browsing |
| Updates | Folder and skill update workflows |
| Settings | Application configuration |

### Layering Model

Use four explicit layers to achieve the immersive floating effect:

| Layer | Purpose | Visual Treatment |
|---|---|---|
| **Layer 0: Window Background** | Foundation and Depth | Deeply blurred, vibrant multi-tonal material (Acrylic/Mica/Desktop wallpaper) |
| **Layer 1: Functional Base** | Structural navigation | High-opacity frosted glass (Sidebar, Title bar background) |
| **Layer 2: Segmented Pills** | Component containers | Floating frosted glass panels for lists, editors, and tools |
| **Layer 3: Floating UI** | Contextual/Transient feedback | Highly vibrant, high-elevation glass (Popovers, Toasts, active Buttons) |

Layering rules:

- All logical UI groups (Quick Copy rows, Skill Lists, Preview Panes) must be encapsulated in floating Layer 2 glass pills.
- Components should appear to hover above the vibrant background with soft shadows and 1px bright inner reflection borders.
- Toolbars and headers within a pill should use subtle tonal variations or thin separators to maintain hierarchy within the glass.
- Buttons and active controls on Layer 3 should have a more pronounced "vibrancy" (higher translucency and light tint).
- Tree rows and list items sit directly on the frosted material of their Layer 2 container, using high-contrast selection states.

### Color

Prefer a vibrant, multi-tonal palette that leverages translucency. Use bright, high-contrast accents and crisp inner reflection borders for glass edges.

| Token | Light (Matte) | Dark (Matte) | Usage |
|---|---:|---:|---|
| `--app-bg` | `#F5F7F9` | `#121214` | Primary application background |
| `--glass-pill` | `#FFFFFF` | `#1E1E22` | Frosted pill containers (Layer 2) |
| `--glass-hover` | `rgba(0,0,0,0.05)`| `rgba(255,255,255,0.08)`| Hover state for pill items |
| `--glass-border` | `#DDE5E1` | `#2A2A30` | 1px Solid border (Reflection edge) |
| `--glass-shadow` | `rgba(0,0,0,0.12)` | `rgba(0,0,0,0.40)` | Depth and elevation shadow |
| `--separator` | `rgba(0,0,0,0.10)` | `rgba(255,255,255,0.10)` | Hairline dividers |
| `--label` | `#111827` | `#F3F4F6` | Primary text (Modern Graphite tint) |
| `--secondary-label`| `rgba(0,0,0,0.55)` | `rgba(255,255,255,0.55)`| Secondary text and hints |
| `--accent` | `#059669` | `#3B82F6` | Modern Blue / Sage active state |
| `--success` | `#10B981` | `#10B981` | Completed / Success indicator |
| `--danger` | `#DC2626` | `#EF4444` | Destructive / Remove actions |

Do not use blue-purple gradients for ordinary UI chrome. The existing logo gradient can remain in the app icon and about/branding surfaces only.

### Glass Fallbacks In PySide6/QML

PySide6 with Qt Quick/QML provides native support for true alpha blending and hardware-accelerated transparency. The previous limitations of CustomTkinter no longer apply:

- **Native Mica/Acrylic:** Use `pywinstyles` or native Qt 6.8+ APIs to apply system materials directly to the `QWindow`.
- **True Alpha Blending:** All QML components support real-time transparency over the native backdrop.
- **Hardware Acceleration:** QML uses the GPU for rendering, ensuring smooth transitions and blur effects.
- **Accessibility:** Continue to provide high-contrast and reduced-transparency modes by mapping QML properties to solid colors via the `Theme.qml` singleton.

### Typography

Use platform-system typography:

```python
font_family = "-apple-system"  # use when available
fallback = "Segoe UI"          # Windows fallback
mono = "SF Mono"               # fallback to Consolas on Windows
```

Recommended scale:

| Role | Size | Weight | Usage |
|---|---:|---|---|
| Large title | 22-24 | Semibold | Window title only |
| Section title | 15-17 | Semibold | Sidebar groups, panel headers |
| Body | 13-14 | Regular | Lists, labels, paths |
| Metadata | 12-13 | Regular | Versions, paths, status details |
| Button | 13-14 | Medium | Toolbar and action buttons |
| Code/content | 12-13 | Regular | `SKILL.md` content views |

Avoid large bold text inside dense panels. Keep text left-aligned. Dense list and tree rows should stay single-line; long paths, descriptions, and skill names should use bounded summaries, truncation, hover quick peek, or a detail inspector instead of forcing row wrapping or horizontal scrolling.

### Corners, Borders, And Materials

- Functional glass shells / Main Window: `12px` (Standardized for OS synchronization).
- Main content surfaces: `10px` to `12px`.
- Buttons and fields: `20px` (Pill style) or `8px` (Compact).
- Repeated row/list items: prefer separators and selection backgrounds.
- Borders: use 1px solid tinted hairlines (`#2D3531`).
- Shadows: use lightly and only for functional floating layers, toasts, popovers, and dialogs.
- Motion: use short, purposeful fades or small translations only when they clarify state. Honor reduced motion by removing movement.

### Motion And List Performance

Skill lists must optimize for immediate response before visual flourish. Category expand/collapse should reduce the active QML delegate set instead of keeping every hidden row mounted at `height: 0`, and row delegates should consume cached model roles for grouping/collapse state instead of doing previous-row lookups in QML. Avoid height animations across bulk list operations; use short hover, focus, color, and inspector transitions where they do not trigger large relayouts.

## Layout Model

### Primary Navigation

Use an Apple-style sidebar for top-level destinations when redesigning the main shell. The sidebar should contain the four stable product areas:

- Quick Copy
- Library
- Updates
- Settings

The sidebar is a functional glass layer. It should feel elevated above the window background but not distract from the list/content layer. The main area should change content based on the sidebar selection. This matches HIG guidance for desktop utilities with hierarchical or productivity-focused content.

### Toolbars

Toolbars are the best place for the Liquid Glass treatment:

- Place frequent actions in a compact glass toolbar.
- Group related actions into segmented clusters or adjacent buttons.
- Keep toolbar labels short.
- Prefer icons for familiar tools, with text where meaning is not obvious.
- Search belongs in the toolbar or immediately below it for searchable views.
- Overflow menus hold lower-frequency commands; they must not be the only access path for common commands.

### Library Layout

The Library uses a segmented "Pill-Stacked" structure to separate navigation, actions, and content:

```text
Library
  Glass Pill 1 (Toolbar): Refresh, Search, Category filter
  Glass Pill 2 (Actions): selected count, Archive, Unarchive, Copy to Projects
  Split Content (Layer 2 Pills):
    Left Pill: Outline tree grouped by category (Single-line summaries)
    Right Pill: Selected skill preview, metadata, and description
  Bottom Status Pill: Counts and result summaries
```

Important behavior:

- **Segmented Focus:** Each pill is a distinct functional unit. This reduces visual density and allows the vibrant background to peek through, creating a sense of organization.
- **Preview Integration:** The preview pane is a sibling pill to the skill list, allowing for a side-by-side comparative experience without overlapping modals.
- **Glass Hover:** Hovering a row in the list pill should use a subtly lightened or tinted selection bar rather than a floating popover, maintaining the integrity of the pill's material.

### Quick Copy Layout

Quick Copy is a vertical stack of specialized glass pills, each controlling a specific aspect of the reference generation workflow:

```text
Quick Copy
  Glass Pill 1 (Context): Refresh, Project selector, Search, Category filter
  Glass Pill 2 (Configuration): Output format menu, Copy Selected, Remove Selected
  Glass Pill 3 (Starred): Combined project skills and command references count
  Glass Pill 4 (Manual Input): Input field, Add, Paste, Browse actions
  Split Content (Layer 2 Pills):
    Left Pill: Skill tree with single-line summaries
    Right Pill: Detailed Skill Inspector with metadata and full content
  Bottom Status Pill: Scan state and visible count
```

Rules:

- **The Stacked Pill Model:** Avoid merging these rows into a single flat panel. The gaps between pills are essential for the Liquid Glass aesthetic.
- **High-Contrast Actions:** Primary buttons like `Copy Selected` or `Copy to Projects` use vibrant fills, while secondary or destructive actions like `Remove Selected` use tinted glass backgrounds with high-contrast text.
- **Inspector Prominence:** The Right Pill (Inspector) is persistent and updates immediately upon selection, providing an ultra-fast verification loop before copying.

### Updates Layout

Projects and skill source updates are one sequential workspace. The user first defines where skills come from and where project copies go, then runs folder sync or source update actions from the same view.

Recommended structure:

```text
Updates
  Glass header: purpose and current update context
  Left project folder pane:
    Source directories list, add/remove/reorder, drag/drop
    Project directories list, add/remove, drag/drop
    Run Folder Update
  Right skill source pane:
    Skill source update rows
    Add Update Source
    Check All Updates
  Bottom glass status: progress, sync results, warnings
```

Sources and projects should feel like two related source lists:

- Use a single Project Folders pane beside the skill-source update list on wide windows.
- Each pane has a compact glass header, list, and toolbar buttons.
- Drag/drop remains supported.
- Reordering sources should use explicit up/down controls and keyboard shortcuts if possible.
- Empty states should explain what to add next without using a modal.

The skill updater should read as a list of update configurations, not a set of large cards.

Each row should show:

- Skill name
- Source type
- Current/latest version
- Last updated
- Status indicator
- Inline actions: Edit, Update, Delete

Use color for status only. Avoid making `Update` green by default; reserve green for completed success. Primary action blue is enough. Add-source/edit-source flows should remain human-friendly: repository URL, path, package, or advanced command fields instead of forcing raw commands first.

## Component Guidance

### Buttons

Use standard-feeling button hierarchy:

| Role | Style |
|---|---|
| Primary action | Blue filled button |
| Secondary action | Neutral filled or bordered button |
| Destructive action | Neutral button with red label or red destructive style only in confirmation |
| Toolbar action | Compact glass/neutral button, icon + label when helpful |
| Repeated row action | Small neutral button or menu item |

Preferred labels:

- `Refresh`
- `Copy Selected`
- `Copy to Projects`
- `Archive`
- `Unarchive`
- `Delete`
- `Add Source`
- `Add Project`
- `Check for Updates`

Avoid vague labels like `OK`. Dialog buttons should use specific verbs such as `Copy Folders`, `Save`, `Delete`, or `Cancel`.

### Search

- Place search near the top of searchable lists, usually inside the glass toolbar.
- Filter as the user types, with a short debounce for large datasets.
- Preserve selected items when filtering if possible.
- Show clear empty states:
  - `No skills match this search.`
  - `No project skills found in configured projects.`
- Support `Ctrl+F` now.

### Menus And Context Menus

Future redesign should introduce predictable menus:

- App/menu bar equivalents where possible: File, Edit, View, Skill, Window, Help.
- Context menus on skill rows and tree items:
  - Open
  - Copy Reference
  - Copy to Projects
  - Archive / Unarchive
  - Reveal in File Explorer
- Commands must not exist only in context menus. They should also be reachable from toolbar/buttons or the menu bar.

### Dialogs, Sheets, Popovers, And Toasts

Use modal dialogs only for focused tasks:

- Add/edit skill update configuration
- Choose project copy projects
- Confirm destructive delete when undo is not available

Dialog rules:

- Use strong regular glass or opaque fallback, not clear glass.
- Title should be short and task-specific.
- Message text should explain consequence, not repeat the button label.
- Primary button goes last/right in the current toolkit convention.
- Destructive actions use red styling and explicit labels.
- For non-critical feedback, prefer inline status labels, toasts, or a bottom status area over message boxes.

Toast rules:

- Toasts use glass-like material and short text.
- Toasts may include one action, such as `Undo`.
- Toasts should not cover active row selection or the main copy/update controls.
- Toasts should auto-dismiss after a short interval unless the action is still relevant.

Popover rules:

- Hover quick peek uses glass-like material but should remain readable over both light and dark content.
- Popovers should dismiss when pointer leaves or focus changes.
- Popovers should never be the only place where important content is available.

### Lists, Trees, And Selection

QML `ListView` and `SmoothListView` handle hierarchical category browsing, replacing the previous `ttk.Treeview` approach.

Required states:

- Hover
- Focus
- Selected
- Disabled
- Archived
- Running
- Skipped
- Failed

Selection rules:

- Multi-selection must be visually obvious.
- Internal selected-item state, visible row markers, and count/status labels must stay synchronized.
- Category rows should look different from skill rows through weight, disclosure state, and subtle background, not through loud color.
- Use accent-colored selection with readable label text; do not rely on color alone.

### Status And Progress

Use a consistent status model:

- Inline count: `24/120 shown`
- Running state: `Scanning configured projects...`
- Success: `Copied 3 skills to 2 projects.`
- Partial failure: `Copied 2 skills. 1 skipped.`
- Failure: `Failed to scan project skills.`

Status can sit in a bottom glass bar when it is part of the functional layer. Progress bars should appear only for meaningful ongoing work and disappear after completion. For indeterminate work, use a small activity indicator style if CustomTkinter support allows it.

## Accessibility Requirements

Every future UI change must satisfy these basics:

- All controls have clear text labels or accessible names.
- Interactive controls are keyboard reachable in a logical order.
- Focus state is visible.
- Color is never the only signal for success, warning, archive, selected, or error.
- Text contrast meets WCAG AA where practical.
- Long paths and names wrap, truncate with tooltips, or expose full text in a detail area.
- Motion and flashing are avoided; any animation must be optional and non-essential.
- Status updates should be textual so they can be read by assistive technologies.
- Reduced transparency mode maps glass surfaces to opaque semantic surfaces.
- Increased contrast mode strengthens borders, selection outlines, and text contrast.

## Keyboard And Pointer Shortcuts

Recommended shortcuts:

| Command | Windows |
|---|---|
| Search current view | `Ctrl+F` |
| Refresh current view | `Ctrl+R` |
| Copy selected/reference | `Ctrl+C` |
| Select all visible | `Ctrl+A` |
| Delete selected | `Delete` |
| Open selected skill | `Enter` |
| Close detail tab/view | `Ctrl+W` |

Pointer behavior:

- Right-click opens context menu.
- Double-click opens skill detail.
- Drag/drop for source and project directories remains supported.
- Hover states should be subtle but visible on buttons and tree rows.
- Glass hover states should change elevation or tint slightly, not jump or glow.

## Branding And Icon Use

The existing logo can remain as the app icon and small title/About-window mark. Do not make branding the dominant interface element.

Logo guidance:

- Use the logo at `24px` to `32px` in toolbar/title contexts.
- Use larger logo only in an About dialog, installer, or README.
- Keep gradient logo out of routine buttons and row icons.

Icon direction:

- Use SF Symbols-inspired line icons where practical.
- On Windows, use simple monochrome icons that match SF Symbol weight and optical size.
- Prefer familiar symbols for toolbar actions: refresh, search, copy, folder, archive, trash, plus, chevron.
- Icons in glass controls should use high-contrast foreground colors and should remain legible when transparency is disabled.

## Implementation Notes For Current Code

Current UI entry points:

- `src/skill_manager/app.py` initializes the PySide6 `QGuiApplication` and QML engine.
- `src/skill_manager/SkillManagerComponents/` contains the declarative UI components (GlassPill, Sidebar, Views).
- `src/skill_manager/SkillManagerComponents/Theme.qml` (Singleton) owns the Liquid Glass tokens and opaque fallbacks.

Implementation status:

1. `Theme.qml` is implemented with Liquid Glass tokens (alpha-enabled) and semantic status colors.
2. `GlassPill.qml`, `Sidebar.qml`, `GlassDropdown.qml`, and other Glass components form the foundational design system.
3. `QuickCopyView.qml`, `LibraryView.qml`, `UpdatesView.qml`, and `SettingsView.qml` are fully migrated to QML, binding to Python core via `QObject` signals and slots.
4. Native Windows 11 Mica effects are integrated via `pywinstyles` and `DwmSetWindowAttribute` APIs.
5. Reduced-transparency and increased-contrast modes are handled via the `Theme` singleton properties.
6. `ScreenshotOverlay.qml` and `ImageInspector.qml` provide screenshot capture and redaction capabilities.
7. `FrostOverlay.qml` provides glass blur effects for popups and menus.
8. `GlassMenu.qml` and `GlassMenuItem.qml` implement ultra-glass context menus.
9. `TopBar.qml` and `CustomTitleBar.qml` handle window chrome and toolbar layout.

Implementation constraints:

- Do not use per-row glass cards in tree/list views.
- Do not introduce decorative animations before layout and state behavior are stable.
- Validate layout at default size and moderately resized windows after each UI phase.

## Non-Goals

- Do not rewrite the app in SwiftUI/AppKit just to achieve the look.
- Do not remove Windows support.
- Do not hide high-frequency workflow controls behind menus.
- Do not prioritize branding over utility.
- Do not use clear glass (no blur) behind text-heavy controls; legibility is mandatory.
- Do not use decorative animations that slow down the workflow.

## Acceptance Checklist

Use this checklist when implementing the Liquid Glass redesign:

- [ ] The app opens to an immersive, vibrant, and fully translucent workspace.
- [ ] The window background utilizes a **Solid Matte** deeply-tinted material (e.g., #0E1210).
- [ ] The main window and primary containers use a **synchronized 12px radius** for OS-level shadow alignment.
- [ ] All functional UI sections are encapsulated in floating frosted glass pills (Layer 2) with 1px solid tinted borders.
- [ ] Gaps between stacked pills allow the primary background to remain visible.
- [ ] Light and dark appearances use the validated hex-based Solid Matte tokens.
- [ ] Reduced-transparency and increased-contrast fallbacks preserve the "pill-stacked" hierarchy.
- [ ] The Quick Copy view follows the modular stack of context, configuration, starred, and manual input pills.
- [ ] The Skill Inspector is persistent and updates immediately on selection.
- [ ] Tree rows and list items sit directly on the frosted glass material.
- [ ] Buttons use vibrant fills (Primary) or tinted glass backgrounds (Secondary/Destructive).
- [ ] Search fields filter instantly and show helpful empty states within their glass containers.
- [ ] UI text is highly legible against the solid matte and blurred materials.
- [ ] No merging of stacked pills into single flat panels occurs.

## Reference Skill Mapping

This guide uses the local HIG skill files as follows:

| Skill file | Applied to |
|---|---|
| `.agents/skills/brainstorming/SKILL.md` | Keep the design direction broad enough to support future UI phases while preserving current workflows |
| `.agents/skills/concise-planning/SKILL.md` | Keep implementation phases compact and ordered |
| `.agents/skills/conductor-implement/SKILL.md` | Treat the guide as implementation-ready direction for future UI work |

## External Design References

- Apple Human Interface Guidelines: Materials, especially Liquid Glass vs. standard materials.
- Apple Developer Documentation: Adopting Liquid Glass and technology overview.

## Icons and Assets

- **Icon Set:** [Lucide](https://lucide.dev/)
- **Sourcing:** Always download raw SVG files directly from the Lucide GitHub repository instead of generating custom icon code. This ensures a standard, sleek line-art design consistency.
- **Download Script Pattern (PowerShell):**
  ```powershell
  Invoke-WebRequest -Uri "https://raw.githubusercontent.com/lucide-icons/lucide/main/icons/<icon-name>.svg" -OutFile "assets/ui/tool-<icon-name>.svg"
  ```
