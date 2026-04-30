## Context

The simulated-factory service (`services/simulated-factory`) is a Python FastAPI application that simulates the physical factory: two Dobot robots, a color sensor, a distance sensor, and a conveyor belt. It has an HTMX-driven UI served from `base.html` with SSE-pushed out-of-band fragment updates.

The current sensor panel uses generic freeform text inputs (`_sensor_card.html`). There is no spatial representation of the factory. The `SimulationState` model already contains `DobotRuntimeState` (position, speed, suction, conveyor state) but this data is not exposed in the UI. The inventory service runs separately at port 8103 and owns the grid state.

## Goals / Non-Goals

**Goals:**
- Replace the sensor panel with a CSS-grid block diagram ("factory twin") showing all five factory components with their live state.
- Surface typed, dropdown-based sensor configuration inline in each component's block.
- Show block location (which factory zone the active block is currently in) derived from the current preset step name.
- Display a read-only inventory grid fetched from the inventory service.

**Non-Goals:**
- Animated item movement between zones.
- Control of the inventory state from simulated-factory.
- Integration with the real physical Dobot (twin reflects simulated state only).
- Mobile-optimized layout (desktop-first, existing responsive breakpoints retained).

## Decisions

### Decision 1: Inventory data via background cache (not HTMX polling or client JS)

The twin panel is rendered server-side by Jinja2 and pushed via the existing SSE OOB stream. Fetching inventory must therefore be non-blocking at render time.

**Chosen approach:** `SimulationEngine` starts an `asyncio.Task` on startup that calls `httpx.AsyncClient.get(INVENTORY_URL + "/inventory")` every 3 seconds and stores the result in `self._inventory_cache`. The twin fragment renderer reads from this cache synchronously.

**Alternatives considered:**
- *HTMX polling (`hx-trigger="every 3s"`)* — would require a synchronous proxy call inside a FastAPI handler, and the inventory sub-block would update independently of the SSE stream, creating a split update model.
- *Client-side JS fetch* — breaks the HTMX-only rendering contract and requires injecting a service URL into the page.

**Trade-off:** 3-second staleness on inventory grid. Acceptable because inventory changes only occur at the start (reserve) and end (fetch/restore) of a manufacturing run, both of which align with preset step transitions that already trigger SSE updates.

### Decision 2: Block location derived from `currentStepName`

No new model field. Step-name-to-zone mapping is a pure template computation:

| `currentStepName` | Active zone |
|---|---|
| `null` or `order-received` | Inventory (reserved cells visible) |
| `pickup` | Conveyor — "ON CONVEYOR" badge |
| `color-check` | Conveyor — "AT PICKUP ZONE" badge |
| `place` / `reject` | Assembly Area — "BEING PLACED / REJECTED" badge |
| idle | No badge |

The mapping is encoded in the Jinja2 template using a simple `if/elif` chain on `state.currentStepName`.

**Alternative considered:** Add a `blockLocation` enum to `SimulationState`. Rejected — the step name already encodes this, adding a parallel field creates a synchronisation risk.

### Decision 3: Sensor controls typed by sensor ID prefix

Sensor type is inferred from the `sensorId` prefix (`color-*`, `ir-*`, `distance-*`). The twin template renders:
- `color-*` → mode `<select>` (fixed/scripted/random) + color `<select>` (RED/GREEN/BLUE/YELLOW) with CSS swatch + raw_color inputs
- `distance-*` → mode `<select>` (fixed/scripted) + numeric value input + scripted_values text input (shown only when mode=scripted)
- `ir-*` → mode `<select>` (fixed/scripted) + boolean `<select>` (true/false)

Sensor PUT endpoint (`PUT /api/config/sensors/{id}`) and `SensorUpdateRequest` model are unchanged. Only the HTML form changes.

### Decision 4: Delete sensors fragment, add twin fragment

`GET /fragments/sensors` and its templates are removed. `GET /fragments/twin` is added. The SSE `_render_all_oob` replaces the `sensors` renderer with `twin`. The `twin` fragment renders the full block diagram including all sensor sub-blocks inline.

## Risks / Trade-offs

- **Inventory service unavailable** → Mitigation: cache returns `None`; twin renders the inventory block with "Unavailable" label. No crash.
- **`httpx` not in `pyproject.toml`** → Mitigation: add as explicit dependency in task T1.
- **Step-name-to-zone mapping breaks with new presets** → Mitigation: document the convention in `presets.yml` comments; unknown step names fall through to a neutral "IN PROGRESS" badge rather than erroring.
- **Twin fragment is large** → The full diagram is one fragment; SSE pushes it on every state change. At ~2 KB of HTML this is acceptable; if it grows, individual sub-blocks can be split into separately-addressable OOB fragments in a future iteration.

## Open Questions

- Should the twin include the right Dobot (`dobots.right`) or only left? Currently only `left` is visible in the factory flow. **Assumption:** show left only; right omitted until needed.
- `INVENTORY_URL` default value assumes local dev (`http://localhost:8103`). Docker Compose networking uses `http://inventory:8103`. Needs to be set in `docker-compose.yml` / `docker-compose-development.yml` for containerized runs.
