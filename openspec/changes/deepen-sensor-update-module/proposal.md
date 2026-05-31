## Why

The sensor update seam between the HTMX frontend and `api.py` is shallow: callers must know form field naming, manual coercion rules, the HX-Request response branch, and that the real visual update arrives through a separate SSE channel. Additionally, the README and OpenSpec still describe per-sensor HTML fragment responses while the actual implementation uses `hx-swap="none"` with SSE OOB refresh — creating contract drift across docs, specs, and tests.

## What Changes

- Consolidate the 60+ lines of ad-hoc input coercion (CSV→list, string→bool/int/float) from the PUT handler into declarative Pydantic field validators on `SensorUpdateRequest`.
- Remove the polymorphic response branch (HTML empty body vs. JSON) from the handler; return JSON consistently and let the SSE OOB stream handle operator visual refresh.
- Update the OpenSpec and README to reflect the actual sensor update contract (no per-sensor HTML fragment response).
- Delete the `HX-Request` detection branch and stale `sensors.html` / `_sensor_card.html` references from documentation.

## Capabilities

### New Capabilities

_(none — this is a deepening of an existing module, not a new feature)_

### Modified Capabilities

- `simulated-factory-service`: Sensor update endpoint removes response polymorphism; always returns JSON. Coercion moves to model validators.
- `simulator-htmx-frontend`: Remove requirement that sensor PUT returns an HTML fragment for HTMX callers. Document SSE OOB refresh as the sole operator visual update channel.
- `factory-twin-diagram`: Remove scenario "Sensor update submitted from twin → returns an updated fragment for the affected sensor zone only"; the twin relies on SSE refresh.

## Impact

- **Code**: `simulated_factory/api.py` PUT handler shrinks significantly; `simulated_factory/models.py` gains field validators.
- **Tests**: `tests/test_api.py` sensor tests update assertions (no more HTML content-type check for HTMX callers; response is always JSON).
- **Frontend**: `templates/fragments/twin.html` already uses `hx-swap="none"` — no template change needed.
- **Documentation**: README.md, DEVELOPER.md, and three OpenSpec spec files updated.
- **Breaking**: **BREAKING** — External callers that relied on `HX-Request: true` returning empty HTML will now receive JSON. The HTMX frontend itself is unaffected because it uses `hx-swap="none"`.
