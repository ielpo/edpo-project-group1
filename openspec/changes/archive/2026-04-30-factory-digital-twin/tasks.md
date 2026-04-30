## 1. Dependencies & Configuration

- [x] 1.1 Add `httpx` to `services/simulated-factory/pyproject.toml` as a runtime dependency
- [x] 1.2 Add `INVENTORY_URL` env var (default `http://localhost:8103`) to `SimulationEngine.__init__` and store on self
- [x] 1.3 Update `docker-compose.yml` and `docker-compose-development.yml` to pass `INVENTORY_URL=http://inventory:8103` to the simulated-factory container

## 2. Inventory Background Cache

- [x] 2.1 Add `_inventory_cache: dict | None = None` attribute to `SimulationEngine`
- [x] 2.2 Add `_start_inventory_poller()` method that launches an `asyncio.Task` calling `httpx.AsyncClient.get(self._inventory_url + "/inventory")` every 3 s, storing result in `_inventory_cache` and swallowing exceptions
- [x] 2.3 Call `_start_inventory_poller()` from the FastAPI `lifespan` startup handler in `api.py`
- [x] 2.4 Add `get_inventory_cache()` method on engine returning `_inventory_cache` or a neutral `{"grid": None, "rows": 0, "cols": 0}` fallback
- [x] 2.5 Add `GET /api/inventory` endpoint in `api.py` returning `engine.get_inventory_cache()` as JSON

## 3. Twin Fragment: Template

- [x] 3.1 Create `templates/fragments/twin.html` with outer `<div id="twin-panel">` and `hx-swap-oob` support
- [x] 3.2 Add Inventory Grid zone: render 5×4 CSS grid from `inventory.grid`; cells styled as occupied/reserved/empty matching dashboard colors; show "Unavailable" label when grid is `None`
- [x] 3.3 Add Conveyor Belt zone: render block location badge using `state.currentStepName` mapping (order-received → nothing, pickup → "ON CONVEYOR", color-check → "AT PICKUP ZONE", place → "BEING PLACED", reject → "BEING REJECTED", other → "IN PROGRESS"); show conveyor direction and speed from `dobots.left`
- [x] 3.4 Add Robot zone: render `dobots.left` position (x, y, z, r), speed, suction enabled as read-only labeled values; no editable controls
- [x] 3.5 Add Assembly Area zone: display active step name and block location badge when applicable
- [x] 3.6 Add Color Sensor zone: inline form with `<select>` for mode (fixed/scripted/random), `<select>` for color value (RED/GREEN/BLUE/YELLOW) with CSS color swatch, raw_color text input; `hx-put="/api/config/sensors/{{ sensor.sensorId }}"` targeting the color sensor zone `id` for OOB swap
- [x] 3.7 Add Distance Sensor zone: inline form with `<select>` for mode (fixed/scripted), `<input type="number">` for fixed value, text input for `scripted_values` (comma-list); `hx-put` targeting the distance sensor zone

## 4. Twin Fragment: Endpoint & SSE Integration

- [x] 4.1 Add `GET /fragments/twin` endpoint in `api.py` that calls `_render_fragment("twin", state=..., sensors=..., inventory=..., oob=False)`
- [x] 4.2 Replace `("sensors", ...)` with `("twin", ...)` in `_render_all_oob` renderers list
- [x] 4.3 Pass `state`, `sensors`, and `inventory` context variables to the twin renderer in `_render_all_oob`

## 5. Page Shell Update

- [x] 5.1 In `base.html`, replace the `<div id="sensor-panel">` section with `<div id="twin-panel" hx-get="/fragments/twin" hx-trigger="load" hx-swap="outerHTML">`
- [x] 5.2 Add CSS in `base.html` for the twin grid layout: 3-column factory floor grid, zone cards, cell grid for inventory, color swatches, and location badge styles

## 6. Cleanup

- [x] 6.1 Delete `templates/fragments/sensors.html`
- [x] 6.2 Delete `templates/fragments/_sensor_card.html`
- [x] 6.3 Remove `GET /fragments/sensors` endpoint from `api.py`

## 7. Tests

- [x] 7.1 Add unit test for `get_inventory_cache()` fallback when cache is `None`
- [x] 7.2 Add unit test for block location badge mapping function (all step name cases)
- [x] 7.3 Add integration smoke-test: `GET /fragments/twin` returns 200 with `id="twin-panel"` in body
- [x] 7.4 Add integration smoke-test: `GET /api/inventory` returns 200 with expected JSON shape
