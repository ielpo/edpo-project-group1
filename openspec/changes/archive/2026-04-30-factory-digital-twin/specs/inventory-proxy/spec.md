## ADDED Requirements

### Requirement: Inventory background cache
The `SimulationEngine` SHALL maintain a background `asyncio.Task` that fetches the inventory grid from `INVENTORY_URL + "/inventory"` every 3 seconds and stores the result in an internal cache. The cache SHALL be initialized to `None` before the first successful fetch.

#### Scenario: Cache populated on first fetch
- **WHEN** the engine starts and the inventory service is reachable
- **THEN** within 3 seconds the cache SHALL contain the inventory grid as returned by `GET /inventory`
- **AND** subsequent renders of the twin fragment SHALL use this cached grid

#### Scenario: Inventory service unavailable
- **WHEN** the inventory service is unreachable (connection error or non-200 response)
- **THEN** the cache SHALL retain its previous value (or `None` if never populated)
- **AND** the engine SHALL NOT raise an exception or stop the background task
- **AND** the twin fragment SHALL render the Inventory Grid zone with an "Unavailable" label

#### Scenario: Cache refreshes after transient failure
- **WHEN** the inventory service becomes reachable again after a failure
- **THEN** the next 3-second poll SHALL successfully update the cache

### Requirement: Inventory proxy endpoint
The service SHALL expose `GET /api/inventory` that returns the current cached inventory grid as JSON.

#### Scenario: Proxy returns cached data
- **WHEN** a client requests `GET /api/inventory`
- **THEN** the service returns `200 OK` with the cached grid payload
- **AND** the response shape matches the inventory service's `GET /inventory` response: `{"grid": [[...]], "rows": 5, "cols": 4}`

#### Scenario: Proxy returns empty when cache is cold
- **WHEN** a client requests `GET /api/inventory` before the first successful fetch
- **THEN** the service returns `200 OK` with `{"grid": null, "rows": 0, "cols": 0}`

### Requirement: INVENTORY_URL configuration
The engine SHALL read the inventory service base URL from the `INVENTORY_URL` environment variable, with a default value of `http://localhost:8103`.

#### Scenario: Default URL used in development
- **WHEN** `INVENTORY_URL` is not set
- **THEN** the engine SHALL connect to `http://localhost:8103/inventory`

#### Scenario: Custom URL used in containerized deployment
- **WHEN** `INVENTORY_URL` is set to `http://inventory:8103`
- **THEN** the engine SHALL connect to `http://inventory:8103/inventory`
