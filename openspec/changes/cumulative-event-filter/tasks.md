## 1. Server-side filter logic

- [ ] 1.1 Add `ALL_EVENT_TYPES` frozenset and `TYPE_LABELS` mapping constant to `events.py`
- [ ] 1.2 Replace `_normalize_filter_mode()` with `parse_filter_types(param: str | None) -> frozenset[str]` that splits on comma, uppercases, strips unknowns, defaults to PROCESS_EVENT_TYPES when None
- [ ] 1.3 Update `EventStore.list_events()` to accept `active_types: frozenset[str]` instead of `filter_mode: str` and filter by set membership
- [ ] 1.4 Add helper `build_filter_param(active_types: frozenset[str]) -> str` that returns the lowercase comma-separated string for URL construction

## 2. API route changes

- [ ] 2.1 Update `_event_filter_mode()` helper in `api.py` to call `parse_filter_types()` and return a `frozenset[str]`
- [ ] 2.2 Update `/fragments/events` route to pass `active_types` to the snapshot view and template context
- [ ] 2.3 Update `/sse/status` route to parse `?filter=` as comma-separated types for OOB renders
- [ ] 2.4 Update `runtime_snapshot.py` `events_view()` to accept and forward `active_types`

## 3. Template changes

- [ ] 3.1 Rewrite `fragments/events.html` chip UI: replace binary toggles with preset row (All, Process, None) and type chip row (9 chips)
- [ ] 3.2 Compute each chip's `hx-get` URL in Jinja from active_types ± toggled type using `build_filter_param()`
- [ ] 3.3 Add `data-active-types` attribute to the event panel div (comma-separated lowercase)
- [ ] 3.4 Update empty-state message to "No events match the current filter"

## 4. SSE reconnect adaptation

- [ ] 4.1 Update `base.html` JS to read `data-active-types` instead of `data-filter-mode`
- [ ] 4.2 Update `history.replaceState` URL construction to use `?filter=<types>`
- [ ] 4.3 Update SSE reconnect URL to `/sse/status?filter=<types>`
- [ ] 4.4 Update initial `hx-get` on the event panel placeholder in `base.html` to omit old `?filter=full`

## 5. Tests

- [ ] 5.1 Update `test_process_event_log.py` filter assertions to use new `?filter=kafka,command,...` format
- [ ] 5.2 Add test for comma-separated type filtering (specific subset)
- [ ] 5.3 Add test for missing param defaults to process set
- [ ] 5.4 Add test for empty param returns no events
- [ ] 5.5 Add test for unknown types silently ignored
- [ ] 5.6 Add test verifying chip URLs contain correct toggle sets
