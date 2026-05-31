## 1. Filter propagation

- [x] 1.1 Add one normalized event-filter mode path in the simulated-factory HTTP layer for `GET /`, `GET /fragments/events`, and `GET /sse/status`.
- [x] 1.2 Thread the selected filter mode through the simulator page shell so the event-panel fragment request and the existing page-wide SSE connection use the same request-scoped mode.

## 2. Event-panel rendering contract

- [x] 2.1 Update the events fragment toggles to request a server-backed filtered panel in place instead of relying on browser-only hide/show behavior.
- [x] 2.2 Add a thin client hook that uses `history.replaceState` and reconnects the existing page-wide SSE stream when the operator changes filter mode.
- [x] 2.3 Remove obsolete client-side filter reapplication and DOM-only hiding logic that duplicates server-rendered filtering semantics.

## 3. Validation

- [x] 3.1 Update focused simulated-factory tests to cover page-shell URLs, in-place filtered event fragment output, URL replacement behavior, and filter-consistent SSE/live-update behavior.
- [x] 3.2 Run the targeted simulated-factory test slice for event filtering and HTMX shell behavior.