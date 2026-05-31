## Why

The simulated-factory UI currently uses the default Material Design 3 purple/violet palette (`#6750a4`), which has no visual relationship to the project's brand or hardware context. A custom five-color palette (`palette.css`) has been defined for the project and should be reflected in the UI, giving the simulator a distinct, cohesive look while keeping the full MD3 design system intact.

## What Changes

- Replace all MD3 color role values in `base.html` with tokens derived from `palette.css`
- **Glaucous** (`#6883ba`) becomes the primary color (replaces violet `#6750a4`)
- **Muted teal** (`#68a691`) becomes the secondary color (replaces grey-purple `#625b71`)
- **Light coral** (`#e0777d`) covers both the tertiary and error roles (replaces MD3 red/pink)
- **Alabaster grey** (`#e9e3e6`) becomes the surface-variant and the base for background/surface tones
- **Jet black** (`#2b303a`) replaces the near-black `#1d1b20` as the on-surface / on-background color
- Fix the one hardcoded violet tint in `.btn-text:hover` (`rgba(103, 80, 164, 0.08)`) to use the glaucous tint
- The semantic green used for the `.status-badge.running` state (`#c2e7c0 / #102a10`) is intentionally kept — green for "running" is universally understood and not covered by the palette
- Light scheme only; no dark-mode variant is introduced

## Capabilities

### New Capabilities
- `simulator-ui-color-palette`: Defines the mapping from `palette.css` named colors to MD3 color role tokens and specifies all derived token values for the light scheme

### Modified Capabilities
- `simulator-htmx-frontend`: The "Material Design 3 visual styling" requirement gains a constraint that the MD3 color roles SHALL be sourced from the project's `palette.css` color set rather than the MD3 default purple baseline

## Impact

- `services/simulated-factory/templates/base.html` — only the CSS custom property values in `:root` and one hardcoded `.btn-text:hover` color change; no HTML structure, layout, or behaviour is affected
- No API changes, no backend changes, no Kafka topics affected
- No dependency additions; all styling is inline CSS in the existing template
