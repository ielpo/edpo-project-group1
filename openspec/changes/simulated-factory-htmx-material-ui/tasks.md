## 1. Dependencies and Project Setup

- [ ] 1.1 Add `jinja2>=3.1` explicitly to `pyproject.toml` dependencies
- [ ] 1.2 Run `uv sync` to confirm dependency resolves cleanly

## 2. Templates Directory

- [ ] 2.1 Create `templates/` directory with `base.html`: page shell with `<head>` (Roboto CDN, htmx CDN, SSE ext CDN, shared CSS), main grid layout, and panel placeholders using `hx-get="/fragments/{panel}" hx-trigger="load"` and `hx-ext="sse" sse-connect="/sse/status"`
- [ ] 2.2 Create `templates/fragments/status.html`: status badge fragment
- [ ] 2.3 Create `templates/fragments/presets.html`: preset card list with `hx-post="/api/presets/run"` run buttons
- [ ] 2.4 Create `templates/fragments/sensors.html`: sensor config cards with inline edit forms using `hx-put="/api/config/sensors/{sensorId}"` and `hx-target` pointing to the individual sensor card
- [ ] 2.5 Create `templates/fragments/events.html`: chronological event list (latest first, max 30 entries)
- [ ] 2.6 Create `templates/fragments/pending.html`: pending action cards with approve/reject buttons (`hx-post="/api/interactive/{id}/resolve"`)

## 3. Material Design 3 CSS

- [ ] 3.1 Define MD3 color role tokens in `:root` (primary, on-primary, secondary, surface, surface-variant, on-surface, on-surface-variant, error, on-error, outline, background)
- [ ] 3.2 Define MD3 elevation overlay tokens (levels 0–5 as surface tint opacity values per spec)
- [ ] 3.3 Define MD3 typescale tokens (display, headline, title, body, label — large/medium/small variants)
- [ ] 3.4 Define MD3 shape tokens (extra-small through extra-large corner radius)
- [ ] 3.5 Implement component styles: card (surface + elevation-1), filled button (primary), text button, outlined text field, chip (assist/filter), divider, navigation bar stub

## 4. API — Fragment and SSE Endpoints

- [ ] 4.1 Add `Jinja2Templates` instance pointing to `templates/` in `api.py`
- [ ] 4.2 Change `GET /` to render `base.html` via `Jinja2Templates`
- [ ] 4.3 Add `GET /fragments/status`, `/fragments/presets`, `/fragments/sensors`, `/fragments/events`, `/fragments/pending` endpoints each returning a `HTMLResponse` from the matching template fragment
- [ ] 4.4 Add `GET /sse/status` as an `EventSourceResponse` (using `sse-starlette` or manual `StreamingResponse`): subscribe to `EventStore`, render updated fragments on each event, send as `text/event-stream` with `hx-swap-oob="true"` wrappers
- [ ] 4.5 Remove the `_ui_html()` helper function from `api.py` (or keep temporarily behind a feature flag)

## 5. Sensor Fragment Partial Update

- [ ] 5.1 Update `PUT /api/config/sensors/{sensorId}` to detect `HX-Request` header and return an HTML fragment for the updated sensor card instead of JSON when called from htmx
- [ ] 5.2 Verify non-htmx callers (e.g., direct API calls) still receive JSON

## 6. Tests and Verification

- [ ] 6.1 Add integration test: `GET /` returns HTML with expected htmx attributes
- [ ] 6.2 Add integration test: `GET /fragments/presets` returns HTML containing preset names from `presets.yml`
- [ ] 6.3 Add integration test: `GET /sse/status` streams `text/event-stream` content-type
- [ ] 6.4 Manual smoke test: open UI in browser, run a preset, confirm all panels update live

## 7. Cleanup and Documentation

- [ ] 7.1 Remove `web/index.html` after smoke test passes
- [ ] 7.2 Update `services/simulated-factory/README.md` to reflect new template structure and htmx/SSE architecture
