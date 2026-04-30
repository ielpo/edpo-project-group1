## 1. Update MD3 color role tokens in base.html

- [x] 1.1 Replace `--md-sys-color-primary` with `#6883ba` (glaucous)
- [x] 1.2 Replace `--md-sys-color-on-primary` — keep `#ffffff`
- [x] 1.3 Replace `--md-sys-color-primary-container` with `#d5e0f5`
- [x] 1.4 Replace `--md-sys-color-on-primary-container` with `#0f233f`
- [x] 1.5 Replace `--md-sys-color-secondary` with `#68a691` (muted teal)
- [x] 1.6 Replace `--md-sys-color-on-secondary` — keep `#ffffff`
- [x] 1.7 Replace `--md-sys-color-secondary-container` with `#c3e4d9`
- [x] 1.8 Replace `--md-sys-color-on-secondary-container` with `#0b2a1f`
- [x] 1.9 Add `--md-sys-color-tertiary: #b83a3f` (darkened light coral)
- [x] 1.10 Add `--md-sys-color-on-tertiary: #ffffff`
- [x] 1.11 Add `--md-sys-color-tertiary-container: #f5c9cb`
- [x] 1.12 Add `--md-sys-color-on-tertiary-container: #3d0a0c`
- [x] 1.13 Replace `--md-sys-color-error` with `#b83a3f`
- [x] 1.14 Replace `--md-sys-color-on-error` — keep `#ffffff`
- [x] 1.15 Replace `--md-sys-color-error-container` with `#f5c9cb`
- [x] 1.16 Replace `--md-sys-color-on-error-container` with `#3d0a0c`
- [x] 1.17 Replace `--md-sys-color-background` with `#f4f1f2`
- [x] 1.18 Replace `--md-sys-color-on-background` with `#2b303a` (jet-black)
- [x] 1.19 Replace `--md-sys-color-surface` with `#f4f1f2`
- [x] 1.20 Replace `--md-sys-color-on-surface` with `#2b303a`
- [x] 1.21 Replace `--md-sys-color-surface-variant` with `#e9e3e6` (alabaster)
- [x] 1.22 Replace `--md-sys-color-on-surface-variant` with `#4a4547`
- [x] 1.23 Replace `--md-sys-color-outline` with `#6b676a`
- [x] 1.24 Replace `--md-sys-color-outline-variant` with `#c8c2c5`

## 2. Fix hardcoded out-of-palette color

- [x] 2.1 In `.btn-text:hover`, replace `rgba(103, 80, 164, 0.08)` with `rgba(104, 131, 186, 0.08)` (glaucous tint)

## 3. Verify semantic green is unchanged

- [x] 3.1 Confirm `.status-badge.running` still uses `background: #c2e7c0; color: #102a10` and has not been altered
