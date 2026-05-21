## Why

The simulated-factory UI currently displays sensor configuration as generic text-input cards with no spatial or conceptual connection to the physical factory layout. Operators cannot intuitively follow where a block is in the manufacturing process, and sensor controls provide no type-safety (freeform strings for color names, mode identifiers, etc.). A digital twin block diagram would make the factory state immediately readable and reduce configuration errors.

## What Changes

- **REMOVE** the existing sensor panel (`/fragments/sensors`, `_sensor_card.html`) and its generic text-input form.
- **ADD** a factory twin panel (`/fragments/twin`) rendered as a CSS-grid block diagram with five spatial zones: Inventory Grid, Conveyor Belt, Robot (Dobot), Color Sensor, Distance Sensor, Assembly Area.
- **ADD** a block location indicator derived from the current preset step name, showing where the active block is in the flow (inventory → conveyor → robot/assembly) without animation.
- **ADD** an inventory grid read from the `inventory` service (`GET /inventory`) via a background cache refreshed every 3 seconds; cells show occupied/reserved/empty state matching the dashboard.
- **ADD** typed inline sensor controls replacing freeform inputs: `<select>` dropdowns for mode and color/boolean values; `<input type="number">` for distance values; color swatch next to color value.
- **MODIFY** the SSE OOB stream to include the new twin panel fragment and exclude the old sensors panel.

## Capabilities

### New Capabilities
- `factory-twin-diagram`: Block diagram panel representing the physical factory with per-component state display and inline sensor configuration controls.
- `inventory-proxy`: Background cache in the engine that fetches and holds the latest inventory grid from the inventory service, exposed via `GET /api/inventory` for the twin fragment.

### Modified Capabilities
- `simulator-htmx-frontend`: The sensor panel and SSE OOB renderers are replaced by the twin panel. The `GET /fragments/sensors` endpoint is removed; `GET /fragments/twin` is added. The SSE stream now includes the twin OOB fragment.

## Impact

- **`services/simulated-factory/simulated_factory/engine.py`**: add `_inventory_cache` dict and a background `asyncio.Task` that calls `httpx.AsyncClient.get(INVENTORY_URL/inventory)` every 3 s.
- **`services/simulated-factory/simulated_factory/api.py`**: add `/fragments/twin` and `/api/inventory` endpoints; remove `/fragments/sensors`; update `_render_all_oob` to swap in the twin fragment.
- **`services/simulated-factory/templates/base.html`**: replace sensor-panel section with twin-panel section.
- **`services/simulated-factory/templates/fragments/twin.html`** (new): full block diagram template.
- **`services/simulated-factory/templates/fragments/sensors.html`** and **`_sensor_card.html`**: deleted.
- **`services/simulated-factory/pyproject.toml`**: add `httpx` dependency.
- New env var `INVENTORY_URL` (default: `http://localhost:8103`) consumed by the engine.
