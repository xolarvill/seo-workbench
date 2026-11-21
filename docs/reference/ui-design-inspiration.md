# UI design references

Use these sources when a visual or interaction request is underspecified. They are direction, not a template: the workbench palette, typography, and accessibility rules still decide the result.

## shadcn/ui

https://ui.shadcn.com

Source for component structure, naming, CVA variants, Radix-backed behavior, and the `@/components/ui` layout. The local primitives in `ui/src/components/ui/` follow this model.

Use it for: component anatomy, state variants, composition, and shadcn CLI conventions.

## Aceternity UI

https://ui.aceternity.com

Source for interaction and motion patterns, especially the sidebar: toggle- or hover-driven expansion, a collapsed icon rail, animated panel width, and separate desktop and mobile navigation.

Use it for: behavior, transitions, and responsive navigation patterns. Do not copy its palettes, gradients, or marketing decoration.

## Fluid Functionalism

https://fluidfunctionalism.com

Source for restrained surfaces and responsive hover feedback: controls acknowledge the pointer continuously instead of switching abruptly. Its component gallery covers forms, navigation, data display, and overlays.

Use it for: micro-interaction feel, surface treatment, and hover states. Keep motion short and respect `prefers-reduced-motion`.

## Applying a reference

1. The user's current instruction wins; then workbench tokens in `ui/src/styles/global.css`; then the closest existing primitive; then these references.
2. Reuse `ui/src/components/ui/` primitives and the shared `StatusPill`, `HelpTooltip`, and `Drawer` wrappers before adding a new pattern.
3. Keep every control keyboard reachable with a visible focus ring and the right `aria-current`, `aria-expanded`, or tooltip when its label is hidden.
4. Add a dependency only when the reference's effect cannot be expressed with the existing Tailwind, Radix, and CSS setup.
