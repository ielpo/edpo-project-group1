## Context

The simulated-factory event panel currently provides a binary toggle between "full log" (all 9 event types) and "process view" (5 curated types). The filtering is server-side: the `?filter=full|process` query param selects a mode, the server filters events before rendering, and the HTMX fragment swap replaces the panel. SSE live updates read the filter from the initial connection URL and push OOB-swapped panel HTML.

This works but is too coarse. Users want to compose their own filter by toggling individual event types on/off — e.g. "show me only Kafka and Sensor events" or "everything except REST."

## Goals / Non-Goals

**Goals:**
- Replace the binary mode toggle with cumulative per-type chip filters
- Preserve the server-side filtering pattern (no client-side show/hide)
- Maintain SSE live-update correctness with the new filter scheme
- Provide preset shortcuts for common combinations

**Non-Goals:**
- Client-side filtering or JS state management
- Per-user persistence of filter state across sessions (cookies/localStorage)
- Pagination changes (remains 30 events per page)
- Changing event type names or adding new event types

## Decisions

### 1. Query parameter format: `?filter=kafka,command,...` (comma-separated lowercase)

**Rationale**: Reuses the existing `filter` param name. Comma-separated is simple to parse (`split(",")`) and construct in Jinja templates. Lowercase in URLs for readability; server normalizes to uppercase for matching.

**Alternatives considered**:
- Repeated param (`?types=KAFKA&types=COMMAND`) — more standard but harder to construct in Jinja chip URLs
- Named presets only (`?filter=process`) — too coarse, defeats the purpose

### 2. Server-computed chip URLs (zero client JS for filtering)

**Rationale**: Each chip's `hx-get` URL is pre-computed by the Jinja template from `active_types ± this_type`. This keeps the filtering 100% server-side and consistent with the HTMX-first architecture. The HTML is slightly larger (each chip has a unique URL) but there are only 9 types + 3 presets.

**Alternatives considered**:
- Client JS builds URL on click — simpler template but introduces JS state management

### 3. SSE reconnect on filter change (filter in connection URL)

**Rationale**: The existing JS in `base.html` already reconnects SSE when the event panel filter changes. We adapt it to read `data-active-types` (comma-separated) from the swapped panel and build the new SSE URL. No server-side session state needed.

**Alternatives considered**:
- Server-side per-subscription state — adds complexity for negligible benefit
- Disable SSE push for events — loses live-update functionality

### 4. Default to Process set when `?filter` is absent

**Rationale**: The process set is the most useful default for operators. Matches the prior default behavior. An explicit `?filter=` (empty string) or `?filter=none` could represent "show nothing" if needed, but missing param = process set.

### 5. Type-to-label mapping as a server-side constant

The 9 types map to short human-friendly chip labels:

| Type | Label |
|------|-------|
| KAFKA | Kafka |
| COMMAND | Command |
| PENDING_ACTION | Pending |
| ACTION_RESOLVED | Resolved |
| SENSOR_REQUEST | Sensor |
| REST | REST |
| STATE | State |
| MQTT | MQTT |
| EVENT | Event |

This constant lives in `events.py` alongside the existing `PROCESS_EVENT_TYPES`.

## Risks / Trade-offs

- **Breaking change**: Old `?filter=full` / `?filter=process` URLs will no longer work. → Acceptable since this is an internal tool with no external consumers. Tests will be updated.
- **Slightly larger HTML**: Each chip carries a full URL. With 12 chips (9 types + 3 presets), this adds ~2KB to the fragment. → Negligible.
- **SSE reconnect on every toggle**: Filter changes cause a brief SSE reconnect. → Acceptable since filter changes are infrequent user actions and reconnection is fast (~50ms local).
