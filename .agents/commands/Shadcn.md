---
name: Shadcn
category: Custom Commands
type: command
date: 2026-07-03
---

### UI Component Constraints (shadcn/ui)
- **Library Selection:** Exclusively use `shadcn/ui` components for standard UI elements (e.g., buttons, inputs, dialogs). 
- **Global Theming:** You MUST maintain default `shadcn/ui` configurations. Rely on CSS variables (e.g., `bg-background`, `text-foreground`) rather than hardcoded Tailwind colors to ensure global style/dark mode compatibility.
- **Documentation Grounding:** Adhere strictly to the official API (https://ui.shadcn.com/docs/components). Do not hallucinate custom props, variants, or complex nested components not found in the standard library.
- **Styling:** Use standard Tailwind CSS utility classes for structural layout. Do not write custom CSS or inline styles.