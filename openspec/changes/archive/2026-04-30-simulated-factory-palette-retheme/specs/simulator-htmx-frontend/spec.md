## Purpose

Ensure the Material Design 3 visual styling uses the project's custom color palette instead of the MD3 default purple baseline.

## Requirements

## MODIFIED Requirements

### Requirement: Material Design 3 visual styling
The service UI SHALL follow Material Design 3 guidelines using custom CSS with MD3 design tokens (color roles, elevation, typescale) as CSS custom properties. It SHALL use the Roboto typeface and SHALL NOT depend on any third-party component library.

The MD3 color role tokens SHALL be sourced from the project's five-color palette as defined in the `simulator-ui-color-palette` capability. The default MD3 purple baseline SHALL NOT be used.

#### Scenario: UI renders with MD3 color roles
- **WHEN** the simulator UI is opened
- **THEN** the page uses the MD3 color role system (primary, surface, surface-variant, error, tertiary, outline) via CSS custom properties
- **AND** all color tokens resolve to values derived from the project palette (glaucous, muted teal, light coral, alabaster grey, jet-black)
- **AND** elevation levels are expressed via surface tint overlays per the MD3 specification
- **AND** the Roboto typeface is applied
