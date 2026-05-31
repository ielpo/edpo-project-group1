## Why

The simulator UI is a single hand-crafted HTML file with bespoke CSS and ~200 lines of vanilla JavaScript for fetch, DOM manipulation, and WebSocket handling. As the feature surface grows (interactive mode, pending action queue, richer sensor controls), maintaining this approach becomes costly. Adopting htmx eliminates the manual DOM layer, and applying Material Design 3 guidelines produces a consistent, modern interface without introducing a build toolchain.

## What Changes

- Replace the vanilla JS fetch-and-render pattern with **htmx** (loaded from CDN) and server-side HTML fragment rendering via **Jinja2** templates.
- Add `/fragments/*` endpoints to FastAPI that return rendered HTML panels (status, presets, sensors, events, pending actions).
- Replace the browser-side WebSocket JSON consumer with a **Server-Sent Events** stream (`/sse/status`) that pushes out-of-band HTML swaps directly.
- Keep the existing `/api/*` JSON endpoints and `/ws/status` WebSocket **unchanged** — they serve `dobot-control` and other API consumers.
- Restyle all UI components using **Material Design 3** custom CSS (design tokens as CSS custom properties, Roboto typeface, MD3 elevation surfaces, color roles, and motion tokens). No third-party component library — custom components only.
- The `web/index.html` single file is replaced by a `templates/` directory with `base.html` and fragment partials.

## Capabilities

### New Capabilities

- `simulator-htmx-frontend`: htmx-driven, server-rendered UI with SSE live updates and MD3 styling.

### Modified Capabilities

- `simulated-factory-service`: Adds Jinja2 template rendering and SSE endpoint alongside the existing JSON API (no breaking changes to existing endpoints).

## Impact

- **`services/simulated-factory/simulated_factory/api.py`**: New `/fragments/*` routes, `/sse/status` endpoint, Jinja2 app setup.
- **`services/simulated-factory/web/index.html`**: Replaced by `services/simulated-factory/templates/`.
- **`services/simulated-factory/pyproject.toml`**: Add `jinja2` dependency (already a transitive dep of FastAPI; explicit pin for clarity).
- **`services/simulated-factory/README.md`**: Updated UI section.
- No changes to `dobot-control` or any other service.
