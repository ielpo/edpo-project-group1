## Context

The current simulator UI is served as a single static `web/index.html` with inline CSS and vanilla JavaScript. The JS layer fetches JSON from `/api/*` endpoints and reconstructs HTML manually on every state change. There is no templating, no component abstraction, and no server-side rendering.

With the interactive-mode change adding a pending-actions panel, and future features likely adding more reactive panels, the manual DOM approach accumulates complexity quickly. htmx offers a simpler mental model: annotate HTML elements with `hx-*` attributes; the server responds with rendered HTML fragments; the browser swaps them in. No JS state machine, no JSON parsing, no manual DOM work.

FastAPI already has Jinja2 support via `fastapi.templating.Jinja2Templates`. The SSE pattern (`text/event-stream`) is native to browsers and requires no WebSocket upgrade handshake.

## Goals / Non-Goals

**Goals:**
- Replace vanilla JS fetch+render loop with htmx and server-rendered fragments.
- Add Server-Sent Events endpoint for live panel updates (replaces WS JSON consumption in the browser).
- Apply Material Design 3 visual language via custom CSS (design tokens, elevation, color roles, typography scale, motion).
- Keep all existing `/api/*` JSON endpoints intact and unchanged.
- Keep `/ws/status` WebSocket for backward compatibility with non-browser consumers.
- No build toolchain — htmx and fonts loaded from CDN, no npm/webpack.

**Non-Goals:**
- Migrating to React, Vue, or any SPA framework.
- Using official Material Web Components (`<md-button>` etc.) — custom CSS only.
- Changing the simulator's data model or API contract.
- Offline / PWA capabilities.

## Decisions

### D1 — htmx from CDN, no build step

Load htmx and the SSE extension via `<script src="https://unpkg.com/htmx.org@2.x/...">`. The service is a local dev tool; CDN availability is acceptable. This keeps the service deployable as a pure Python container with no Node.js build stage.

**Alternatives considered:**
- Bundle htmx into the container image — clean for offline use but adds Dockerfile complexity for a minor gain.
- Full SPA (React + MUI) — proper ecosystem but introduces a build step, `node_modules`, and a completely different mental model from the rest of the Python service.

### D2 — Dual rendering: JSON API + HTML fragments in parallel

All existing `/api/*` routes remain unchanged. New `/fragments/{panel}` routes accept GET requests from htmx and return rendered HTML. The SSE stream at `/sse/status` sends `hx-swap-oob` HTML fragments so panels update without a full-page reload.

This separation ensures `dobot-control` and external tools are not affected by the UI change.

```
GET /fragments/status   → <div id="status-panel">...</div>
GET /fragments/presets  → <div id="preset-list">...</div>
GET /fragments/sensors  → <div id="sensor-list">...</div>
GET /fragments/events   → <div id="event-list">...</div>
GET /fragments/pending  → <div id="pending-panel">...</div>  (interactive mode)

GET /sse/status         → text/event-stream
                          event: update
                          data: <div id="status-panel" hx-swap-oob="true">...</div>
                                <div id="pending-panel" hx-swap-oob="true">...</div>
```

### D3 — SSE replaces WS for browser live updates

The current WS sends JSON; the browser JS re-fetches all panels on each message. With htmx, the SSE stream sends pre-rendered HTML directly into the right DOM nodes via out-of-band (OOB) swaps. The WS JSON endpoint is kept for `dobot-control` and other API consumers.

**Alternatives considered:**
- WebSocket with htmx-ext-ws — works, but WS requires upgrade handshake and is harder to debug with browser devtools. SSE is simpler for unidirectional push.
- Polling via `hx-trigger="every 2s"` — simplest possible approach, acceptable latency for a dev tool, but wasteful when nothing changes. SSE is more efficient and still simple.

### D4 — Material Design 3 via CSS custom properties only

Define MD3 color roles (`--md-sys-color-primary`, `--md-sys-color-surface`, etc.), elevation tokens (`--md-sys-elevation-1` through `5`), and typescale tokens as CSS custom properties on `:root`. Components (cards, buttons, chips, input fields) are custom HTML + CSS using these tokens. Roboto font loaded via Google Fonts CDN.

This achieves the MD3 look without the weight and complexity of Material Web Components (MWC), which require ES module bundling and shadow DOM management.

**MD3 color roles used:**
- `primary` / `on-primary` — action buttons, active states
- `surface` / `on-surface` — card backgrounds
- `surface-variant` / `on-surface-variant` — secondary content, sensor chips
- `error` / `on-error` — failure/reject buttons
- `outline` — borders, dividers

### D5 — Template structure

```
templates/
├── base.html               full page shell (head, nav, main grid)
└── fragments/
    ├── status.html         status badge panel
    ├── presets.html        preset cards with run button
    ├── sensors.html        sensor config cards with inline edit forms
    ├── events.html         event history list
    └── pending.html        pending action cards (interactive mode)
```

`base.html` uses `hx-get="/fragments/{panel}"` with `hx-trigger="load"` for initial render, and `hx-ext="sse"` with `sse-connect="/sse/status"` for live updates.

## Risks / Trade-offs

| Risk | Mitigation |
|---|---|
| CDN unavailable in offline/air-gapped dev environments | Document CDN deps in README; provide fallback local vendor path in Dockerfile comment |
| SSE connection drops silently | htmx SSE extension auto-reconnects; add visible connection indicator in status panel |
| OOB swaps with many panels create large SSE payloads | Only push panels that actually changed (track dirty state in EventStore notifications) |
| Jinja2 template escaping breaks JSON in `hx-vals` | Use `tojson` filter and careful quoting; cover with integration tests |

## Migration Plan

1. Add `jinja2` to `pyproject.toml` (already transitively available via Starlette, but pin explicitly).
2. Create `templates/` directory with `base.html` and all fragment partials.
3. Add `/fragments/*` and `/sse/status` routes to `api.py`.
4. Change `GET /` to serve `base.html` via `Jinja2Templates`.
5. Remove `web/index.html` and the `_ui_html()` helper function in `api.py`.
6. Smoke test: open UI, verify all panels load and live-update on preset run.

Rollback: revert `api.py` `GET /` to return `_ui_html()` inline HTML (keep the function until the change is verified).

## Open Questions

- Should the SSE stream push all panels or only the changed ones? (Suggested: start simple — push all on any event; optimize later if payload size is a concern.)
- Should the sensor edit form submit via `hx-put` and return an updated sensor fragment? (Suggested: yes — cleaner than a full-panel refresh.)
