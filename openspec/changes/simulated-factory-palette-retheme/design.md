## Context

The simulated-factory UI is a server-rendered htmx frontend served by a Python FastAPI service. All styling lives in a single inline `<style>` block inside `templates/base.html`, built entirely on MD3 CSS custom properties (design tokens). The current light scheme is derived from the MD3 default purple baseline (`#6750a4`). No external CSS framework is used.

A five-color project palette (`palette.css`) has been defined:

| Name | Hex | HSL |
|---|---|---|
| jet-black | `#2b303a` | 220 15% 20% |
| glaucous | `#6883ba` | 220 37% 57% |
| alabaster grey | `#e9e3e6` | 330 12% 90% |
| muted teal | `#68a691` | 160 26% 53% |
| light coral | `#e0777d` | 357 63% 67% |

## Goals / Non-Goals

**Goals:**
- Map the five palette colors onto the full MD3 color role token set
- Preserve the complete MD3 role structure (primary, secondary, tertiary, error, surface, outline families)
- Light scheme only
- Fix the one hardcoded violet tint in `.btn-text:hover`
- All changes contained in `templates/base.html`

**Non-Goals:**
- Dark mode / `prefers-color-scheme` support
- Changing any HTML structure, layout, or component behaviour
- Applying this palette to any other service

## Decisions

### Decision: Glaucous as primary

**Glaucous** (`#6883ba`) replaces `#6750a4` as the primary role. It is the most prominent chromatic color in the palette and fits the same role (interactive elements, filled buttons, active states).

Contrast note: `#6883ba` on `#ffffff` ≈ 3.8:1 — passes WCAG AA for large text and UI components (≥ 3:1) but not body text. Primary is only used on filled buttons, badges, and active chips (never as inline body text), so this is acceptable.

Derived tokens:
| Token | Value | Notes |
|---|---|---|
| `--md-sys-color-primary` | `#6883ba` | glaucous direct |
| `--md-sys-color-on-primary` | `#ffffff` | |
| `--md-sys-color-primary-container` | `#d5e0f5` | glaucous at ~25% saturation / tone 90 |
| `--md-sys-color-on-primary-container` | `#0f233f` | dark navy, high contrast on container |

### Decision: Muted teal as secondary

**Muted teal** (`#68a691`) replaces the grey-purple secondary. Teal provides sufficient hue separation from glaucous (blue) to function as a distinct secondary role.

Derived tokens:
| Token | Value | Notes |
|---|---|---|
| `--md-sys-color-secondary` | `#68a691` | muted-teal direct |
| `--md-sys-color-on-secondary` | `#ffffff` | |
| `--md-sys-color-secondary-container` | `#c3e4d9` | teal at tone 90 |
| `--md-sys-color-on-secondary-container` | `#0b2a1f` | deep teal |

### Decision: Light coral covers both tertiary and error roles

Light coral (`#e0777d`) is the only warm/alert color in the palette. It is used as the source for both tertiary and error roles. Using one source color for both roles is acceptable here because:
- Tertiary is used sparingly (no current active use in templates)
- Error and tertiary being visually similar is preferable to inventing a sixth out-of-palette color
- Both roles share the same container derivation

Because `#e0777d` (luminance ≈ 0.307) cannot serve as a background with white text at 4.5:1, a darkened variant is used for the role color itself:

| Token | Value | Notes |
|---|---|---|
| `--md-sys-color-tertiary` | `#b83a3f` | darkened coral, ~4.5:1 vs white |
| `--md-sys-color-on-tertiary` | `#ffffff` | |
| `--md-sys-color-error` | `#b83a3f` | same as tertiary in this palette |
| `--md-sys-color-on-error` | `#ffffff` | |
| `--md-sys-color-error-container` | `#f5c9cb` | light coral tint, tone 90 |
| `--md-sys-color-on-error-container` | `#3d0a0c` | |
| `--md-sys-color-tertiary-container` | `#f5c9cb` | same as error-container |
| `--md-sys-color-on-tertiary-container` | `#3d0a0c` | |

### Decision: Alabaster as surface-variant; derived tones for surface/background

Alabaster (`#e9e3e6`, tone ~90) is used directly as `surface-variant`. Surface and background are derived by lifting alabaster toward tone 99 (near-white with the same warm grey hue):

| Token | Value | Notes |
|---|---|---|
| `--md-sys-color-background` | `#f4f1f2` | alabaster at tone 99 |
| `--md-sys-color-surface` | `#f4f1f2` | same as background |
| `--md-sys-color-surface-variant` | `#e9e3e6` | alabaster direct |
| `--md-sys-color-outline-variant` | `#c8c2c5` | alabaster darkened one step |
| `--md-sys-color-outline` | `#6b676a` | mid-point between alabaster and jet-black |

### Decision: Jet-black as on-surface

**Jet-black** (`#2b303a`) replaces `#1d1b20` as the on-surface and on-background color. It has a slight cool blue-grey cast that harmonizes with glaucous.

| Token | Value | Notes |
|---|---|---|
| `--md-sys-color-on-background` | `#2b303a` | jet-black direct |
| `--md-sys-color-on-surface` | `#2b303a` | jet-black direct |
| `--md-sys-color-on-surface-variant` | `#4a4547` | mid-step, warm grey |

### Decision: Keep semantic green for running badge

The `.status-badge.running` hardcoded green (`#c2e7c0 / #102a10`) is intentionally unchanged. Green = running is a universal convention and the palette does not include a green.

### Decision: Fix hardcoded hover tint

`.btn-text:hover` has `background: rgba(103, 80, 164, 0.08)` (violet tint). This changes to `rgba(104, 131, 186, 0.08)` (glaucous tint) to match the new primary.

## Risks / Trade-offs

- **Primary contrast at 3.8:1** → Acceptable for UI components and large text; primary is never used as inline body text. Document in spec.
- **Tertiary = error visually** → Both derive from coral. In practice tertiary has no active usage in current templates, so collision is theoretical only.
- **`surface-tint` inherits primary** → `--md-sys-color-surface-tint: var(--md-sys-color-primary)` remains as-is; elevation overlays will now use the glaucous tint automatically, which is correct MD3 behaviour.
