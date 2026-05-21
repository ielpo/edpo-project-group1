# Simulator UI Color Palette

Version: v1

## ADDED Requirements

### Requirement: Palette-derived MD3 color tokens
The simulated-factory UI SHALL define all MD3 color role tokens using values derived from the five project palette colors: jet-black (`#2b303a`), glaucous (`#6883ba`), alabaster grey (`#e9e3e6`), muted teal (`#68a691`), and light coral (`#e0777d`).

The token values SHALL be:

| Token | Value |
|---|---|
| `--md-sys-color-primary` | `#6883ba` |
| `--md-sys-color-on-primary` | `#ffffff` |
| `--md-sys-color-primary-container` | `#d5e0f5` |
| `--md-sys-color-on-primary-container` | `#0f233f` |
| `--md-sys-color-secondary` | `#68a691` |
| `--md-sys-color-on-secondary` | `#ffffff` |
| `--md-sys-color-secondary-container` | `#c3e4d9` |
| `--md-sys-color-on-secondary-container` | `#0b2a1f` |
| `--md-sys-color-tertiary` | `#b83a3f` |
| `--md-sys-color-on-tertiary` | `#ffffff` |
| `--md-sys-color-tertiary-container` | `#f5c9cb` |
| `--md-sys-color-on-tertiary-container` | `#3d0a0c` |
| `--md-sys-color-error` | `#b83a3f` |
| `--md-sys-color-on-error` | `#ffffff` |
| `--md-sys-color-error-container` | `#f5c9cb` |
| `--md-sys-color-on-error-container` | `#3d0a0c` |
| `--md-sys-color-background` | `#f4f1f2` |
| `--md-sys-color-on-background` | `#2b303a` |
| `--md-sys-color-surface` | `#f4f1f2` |
| `--md-sys-color-on-surface` | `#2b303a` |
| `--md-sys-color-surface-variant` | `#e9e3e6` |
| `--md-sys-color-on-surface-variant` | `#4a4547` |
| `--md-sys-color-outline` | `#6b676a` |
| `--md-sys-color-outline-variant` | `#c8c2c5` |

#### Scenario: UI renders with palette-derived primary color
- **WHEN** the simulator UI is opened
- **THEN** the primary color token resolves to `#6883ba` (glaucous)
- **AND** filled buttons and active indicators use the glaucous-derived primary

#### Scenario: UI renders with palette-derived surface colors
- **WHEN** the simulator UI is opened
- **THEN** the background and surface tokens resolve to `#f4f1f2` (alabaster tone 99)
- **AND** surface-variant resolves to `#e9e3e6` (alabaster direct)
- **AND** on-surface resolves to `#2b303a` (jet-black)

#### Scenario: UI renders with palette-derived error/tertiary colors
- **WHEN** an error or tertiary state is displayed
- **THEN** the error and tertiary role tokens resolve to `#b83a3f` (darkened coral)
- **AND** error/tertiary containers resolve to `#f5c9cb` (light coral tint)

### Requirement: No out-of-palette hardcoded color tints
The simulated-factory `base.html` SHALL NOT contain any hardcoded color tints derived from the previous violet palette. All interactive state colors (hover, focus tints) SHALL use palette-derived values.

#### Scenario: Text button hover uses glaucous tint
- **WHEN** an operator hovers over a `.btn-text` button
- **THEN** the hover background tint uses `rgba(104, 131, 186, 0.08)` (glaucous at 8% opacity)
- **AND** no violet-derived tint (`rgba(103, 80, 164, ...)`) appears anywhere in the stylesheet

### Requirement: Semantic running-state color preserved
The `.status-badge.running` state SHALL continue to use the semantic green (`#c2e7c0` background, `#102a10` text) independent of the project palette, as green for "running" is a universal operational convention.

#### Scenario: Running status badge renders green
- **WHEN** the simulator is in a running state
- **THEN** the status badge background is `#c2e7c0` and text is `#102a10`
- **AND** this color is independent of the project palette tokens
