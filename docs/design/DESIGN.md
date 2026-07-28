# SEO Workbench UI design system

## 1. Visual theme and atmosphere

The interface is an editorial instrument panel: calm enough for writing, precise enough for audit evidence, and dense enough for daily analyst work. It combines a graphite application rail with paper-white work surfaces, tabular evidence, and restrained emerald activity signals.

Reference concepts:

- `concepts/workbench-overview-desktop.png`
- `concepts/workbench-markdown-editor.png`
- `concepts/workbench-overview-mobile.png`

## 2. Color palette and roles

| Token | Value | Role |
| --- | --- | --- |
| `canvas` | `oklch(0.965 0.006 145)` / `#F4F5F1` | Application canvas |
| `surface` | `oklch(1 0 0)` / `#FFFFFF` | Editor and evidence surfaces |
| `graphite` | `oklch(0.205 0.008 160)` / `#171A19` | Primary navigation |
| `ink` | `oklch(0.225 0.006 160)` / `#1B1E1D` | Primary text |
| `muted` | `oklch(0.55 0.012 155)` / `#707772` | Secondary text |
| `separator` | `oklch(0.885 0.009 145)` / `#D9DDD8` | Dividers and table rules |
| `emerald` | `oklch(0.56 0.12 165)` / `#138A68` | Ready, current, connected |
| `amber` | `oklch(0.65 0.13 75)` / `#C88721` | Needs setup, conflict |
| `regression` | `oklch(0.55 0.16 28)` / `#BF4D45` | Poor metrics and regressions |

All fills are flat. Gradients, glass surfaces, and decorative glow are prohibited.

## 3. Typography rules

- UI and content chrome: `Archivo`, with `PingFang SC`, `Noto Sans CJK SC`, and system sans fallbacks.
- Metrics and editor source: `Azeret Mono`, with `SFMono-Regular` and monospace fallbacks.
- Rendered Markdown: `Charter`, `Source Han Serif SC`, and serif fallbacks for headings; the UI sans stack for body copy.
- Main project title: 28px, weight 650, line-height 1.1, letter-spacing `-0.012em`.
- Section heading: 14px, weight 650, line-height 1.2.
- Control text: 13px, weight 550, line-height 1.2.
- Body and table text: 14px, weight 400, line-height 1.5.
- Metadata: 12px, weight 500, line-height 1.35.
- All metrics use tabular numerals and right alignment where compared vertically.

## 4. Component styling

- Buttons use a fixed 6px radius, 40px minimum height, a 1px separator border for secondary actions, and a flat emerald fill for the single primary action.
- Navigation rows are flush list rows, not cards. Selected rows use a lighter graphite background step and stronger text.
- Evidence modules use open tables, rails, and bands. Borders separate rows; shadows are reserved for transient elevated surfaces only.
- Inputs use a 6px radius, surface background, 1px separator border, and a 2px emerald focus ring with offset.
- Status is expressed with a dot, icon, text color, or connected rail. Decorative pill badges are not used.
- Icons are 1.5px outline icons with rounded joins and `currentColor`.

## 5. Layout principles

- Desktop shell: 220px application navigation, flexible content workspace, 200px evidence rail where the screen supports it.
- Editor shell: application navigation, 250px file tree, source editor, rendered preview.
- Spacing scale: 4, 8, 12, 16, 24, 32px.
- Dense vertical rhythm is achieved through aligned rows and generous column gaps, not oversized row padding.
- Radius scale: 4px for compact controls, 6px for buttons and inputs, 10px for the few elevated surfaces.

## 6. Depth and elevation

Surface hierarchy uses background-color steps and 1px separators. The graphite navigation is the lowest visual plane, the canvas is the workspace plane, and true-white editor or report surfaces are the reading plane. Drop shadows are limited to menus and transient floating controls.

## 7. Do and do not

- Do keep project files and audit evidence visually distinct.
- Do prioritize the next workflow action and evidence readiness.
- Do preserve tables and lists for comparable data.
- Do show agent updates without stealing focus.
- Do keep one strong primary action per screen.
- Do not use repeated rounded dashboard cards.
- Do show credential readiness, scope, identity metadata, and safe next actions in Integrations.
- Do not reveal secret values, runtime paths, OAuth tokens, private keys, or API keys after submission.
- Do not overwrite a locally edited Markdown document after an agent update.
- Do not invent audit metrics or dates.
- Do not add decorative motion.

## 8. Responsive behavior

- At 1100px, the evidence rail moves below the main evidence workspace.
- At 760px, the desktop navigation becomes a graphite top bar and a three-item bottom navigation.
- Evidence status becomes a horizontally scrollable connected track.
- Editor source and preview become switchable full-width modes; split view is desktop-only.
- Every touch target is at least 44px and safe-area insets are respected.

## 9. Agent prompt guide

- Create a status row on `#FFFFFF`, 44px high, separated by `#D9DDD8`, with 14px Archivo text, a 12px metadata line, a 1.5px outline icon, and a flat `#138A68` ready state. Use 4px radius only when the row is selected.
- Create a graphite navigation row on `#171A19`, 44px high, 16px horizontal padding, 14px weight 550 text, and a 20px outline icon. Selected state uses `oklch(0.29 0.008 160)` and a 3px emerald activity mark.
- Create an evidence table with left-aligned labels, right-aligned Azeret Mono metrics, 16px column gaps, 1px `#D9DDD8` row rules, and no enclosing card shadow.
- Create a primary action button with a flat `#138A68` background, white 13px weight 650 text, 6px radius, 40px height, and `scale(0.96)` press feedback.
- Create an inline conflict strip with a pale amber background, `#C88721` icon and border, 14px message text, three 40px actions, and no modal or overlay.
