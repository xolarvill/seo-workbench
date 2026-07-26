# SEO Workbench extension design system

## 1. Visual theme and atmosphere

The side panel is a compact editorial instrument: true-white reading surfaces, a graphite header, thin rules, and restrained emerald activity. It is dense but never card-heavy. Page facts, provenance, and actions remain visually distinct.

Concept reference: `concepts/seo-workbench-extension.png`.

## 2. Color palette and roles

| Token | Value | Role |
| --- | --- | --- |
| canvas | `oklch(0.965 0.006 145)` / `#F4F5F1` | Extension frame |
| surface | `oklch(1 0 0)` / `#FFFFFF` | Reading surface |
| graphite | `oklch(0.205 0.008 160)` / `#171A19` | Header and mark |
| ink | `oklch(0.225 0.006 160)` / `#1B1E1D` | Primary text |
| muted | `oklch(0.55 0.012 155)` / `#707772` | Secondary text |
| separator | `oklch(0.885 0.009 145)` / `#D9DDD8` | Rules |
| emerald | `oklch(0.56 0.12 165)` / `#138A68` | Current, valid, primary action |
| amber | `oklch(0.65 0.13 75)` / `#C88721` | Warning and partial |
| regression | `oklch(0.55 0.16 28)` / `#BF4D45` | Blocking issue |

## 3. Typography rules

Use Archivo with PingFang SC and system fallbacks for UI copy, and Azeret Mono with SFMono-Regular for counts, URLs, and timestamps. Panel title is 16px/650, section labels 11px/650 uppercase, body and controls 13px, metadata 11px. Metrics use tabular numerals.

## 4. Component styling

Rows are open, 44px minimum, and divided by 1px separators. Buttons use a fixed 6px radius, never pills. The only strong filled action is **Save capture**. Status always combines icon or dot, color, and text. Tabs use text plus a 2px selected underline.

## 5. Layout principles

Design for 360px to 520px side-panel widths. Use an 8px base spacing scale: 4, 8, 12, 16, 24, 32. Sections are full-width bands and tables, not nested cards. Long values wrap or truncate with an accessible title.

## 6. Depth and elevation

Hierarchy comes from background steps and separators. Shadows are reserved for transient controls. No gradient, glass, glow, or decorative elevation.

## 7. Do and do not

- Do distinguish browser observation from Workbench evidence.
- Do keep the panel useful when disconnected.
- Do provide activity feedback for every scan and save.
- Do preserve one primary action per view.
- Do not infer traffic, ranking, or authority.
- Do not capture private browser storage or form content.
- Do not use color alone for status.
- Do not add decorative cards or motion.

## 8. Responsive behavior

Below 390px, summary metrics remain three equal columns and labels shorten before controls shrink. Tabs scroll horizontally. Every action remains at least 40px high. Reduced-motion mode removes scan translation and uses a static progress state.

## 9. Agent prompt guide

- Create a 44px fact row on `#FFFFFF` with a `#D9DDD8` bottom rule, 13px Archivo text, 11px muted metadata, and a right-aligned tabular value.
- Create the single primary button with `#138A68`, white 13px/650 text, 6px radius, 44px height, and `scale(0.96)` press feedback.
- Create a graphite header on `#171A19`, 56px high, `#F0F2F0` text, and one 8px emerald connection dot with a text label.
- Create a five-tab rail with 40px targets, 12px/600 text, and a 2px emerald underline only on the selected tab.
- Create an inline error band with `#BF4D45` text and icon, plain language, a retry button, and no modal.

