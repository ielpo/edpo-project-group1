## Why

The simulator event panel already exposes `Full log` and `Process view`, but the current contract does not require the selected mode to drive the server-rendered fragment or the live SSE stream. That leaves a gap where the browser can show a locally filtered view while the backend continues to send unfiltered event-panel updates, especially during out-of-band refreshes. The desired UX also avoids a full page reload when the filter changes, so the contract needs to describe how a lightweight client hook coordinates page-level live updates with server-rendered filtering.

## What Changes

- Define the event-panel filter as a server-authoritative request input backed by the `filter` query parameter.
- Require the simulator page shell to propagate the selected filter mode into the event fragment request and the existing page-wide SSE connection used for live updates.
- Specify a thin client coordination hook that updates the current URL with `replaceState` and reconnects the existing SSE stream when the operator changes filter mode without reloading the full page.
- Clarify that the event fragment and SSE out-of-band updates must render the same filtered event list for the selected mode.
- Preserve complete backend event history regardless of which filtered view is rendered to the operator.
- Add focused coverage for in-place filtered fragment rendering, URL replacement behavior, and filter-consistent SSE updates.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `simulator-htmx-frontend`: change the event-panel toggle contract so the selected mode is carried through server-rendered fragment and live-update requests.
- `simulated-factory-read-model`: tighten the shared snapshot requirement so fragment rendering and SSE updates consume the same selected event-filter input.

## Impact

- Affects the simulated-factory HTMX shell, event fragment, and request routing for the selected event filter mode.
- Affects the thin client logic that coordinates URL replacement and page-wide SSE reconnection when the filter changes in place.
- Affects SSE update behavior for the event panel so live updates stay aligned with the operator-selected filter.
- Requires updates to simulator frontend/read-model specs and corresponding simulator tests.