## 1. Server-side filter logic

- [x] 1.1 Add `ALL_EVENT_TYPES` frozenset and `TYPE_LABELS` mapping constant to `events.py`
- [x] 1.2 Replace `_normalize_filter_mode()` with `parse_filter_types(param: str | None) -> frozenset[str]` that splits on comma, uppercases, strips unknowns, defaults to PROCESS_EVENT_TYPES when None
- [x] 1.3 Update `EventStore.list_events()` to accept `active_types: frozenset[str]` instead of `filter_mode: str` and filter by set membership
- [x] 1.4 Add helper `build_filter_param(active_types: frozenset[str]) -> str` that returns the lowercase comma-separated string for URL construction

## 2. API route changes

- [x] 2.1 Update `_event_filter_mode()` helper in `api.py` to call `parse_filter_types()` and return a `frozenset[str]`
- [x] 2.2 Update `/fragments/events` route to pass `active_types` to the snapshot view and template context
- [x] 2.3 Update `/sse/status` route to parse `?filter=` as comma-separated types for OOB renders
- [x] 2.4 Update `runtime_snapshot.py` `events_view()` to accept and forward `active_types`

## 3. Template changes

- [x] 3.1 Rewrite `fragments/events.html` chip UI: replace binary toggles with preset row (All, Process, None) and type chip row (9 chips)
- [x] 3.2 Compute each chip's `hx-get` URL in Jinja from active_types ± toggled type using `build_filter_param()`
- [x] 3.3 Add `data-active-types` attribute to the event panel div (comma-separated lowercase)
- [x] 3.4 Update empty-state message to "No events match the current filter"

## 4. SSE reconnect adaptation

- [x] 4.1 Update `base.html` JS to read `data-active-types` instead of `data-filter-mode`
- [x] 4.2 Update `history.replaceState` URL construction to use `?filter=<types>`
- [x] 4.3 Update SSE reconnect URL to `/sse/status?filter=<types>`
- [x] 4.4 Update initial `hx-get` on the event panel placeholder in `base.html` to omit old `?filter=full`

## 5. Tests

- [x] 5.1 Update `test_process_event_log.py` filter assertions to use new `?filter=kafka,command,...` format
- [x] 5.2 Add test for comma-separated type filtering (specific subset)
- [x] 5.3 Add test for missing param defaults to process set
- [x] 5.4 Add test for empty param returns no events
- [x] 5.5 Add test for unknown types silently ignored
- [x] 5.6 Add test verifying chip URLs contain correct toggle sets
