## Why

The event panel currently offers only two filter modes (full debug log vs. a curated "process" view). Users need finer-grained control to isolate specific event types during debugging and monitoring — e.g. showing only Kafka + Sensor events, or everything except REST noise. A cumulative multi-select filter lets users compose exactly the view they need.

## What Changes

- **BREAKING**: Remove the old binary `?filter=full|process` query parameter. Replace with `?filter=<comma-separated-types>` (e.g. `?filter=kafka,command,sensor_request`).
- Add individual type-filter chips (Kafka, Command, Pending, Resolved, Sensor, REST, State, MQTT, Event) that are independently togglable.
- Add preset shortcuts (All, Process, None) that bulk-set the type chips.
- Each chip's `hx-get` URL is server-computed from the current active set ± the toggled type.
- Default to the Process set when no `?filter` param is present.
- Adapt the SSE reconnect logic to pass the active types via the connection URL.
- Unknown type values in the param are silently ignored; empty selection shows a "no events match" message.

## Capabilities

### New Capabilities
- `cumulative-event-filter`: Server-side cumulative type filtering for the event panel with multi-select chip UI, preset shortcuts, and SSE-aware reconnect.

### Modified Capabilities
- `simulator-htmx-frontend`: The events fragment endpoint changes its filter contract from a mode enum to a comma-separated type list. SSE reconnect behavior changes accordingly.

## Impact

- `simulated_factory/events.py` — replace mode-based filtering with set-intersection logic
- `simulated_factory/api.py` — parse `?filter=` as comma list, normalize to uppercase, ignore unknowns
- `simulated_factory/runtime_snapshot.py` — pass active types set to view model
- `templates/fragments/events.html` — new chip UI with server-computed toggle URLs
- `templates/base.html` — adapt SSE reconnect JS to use `data-active-types` attribute
- `tests/test_process_event_log.py` — update all filter param assertions for new format
