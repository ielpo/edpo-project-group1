## MODIFIED Requirements

### Requirement: Inventory background cache
The `InventoryPoller` adapter SHALL maintain a background `asyncio.Task` that fetches the inventory grid from `INVENTORY_URL + "/inventory"` every 3 seconds and stores the result in an internal cache. The cache SHALL be initialized to `None` before the first successful fetch. The `SimulationEngine` SHALL delegate cache reads to the injected `InventoryPoller` instance.

#### Scenario: Cache populated on first fetch
- **WHEN** the inventory poller starts and the inventory service is reachable
- **THEN** within 3 seconds the cache SHALL contain the inventory grid as returned by `GET /inventory`
- **AND** subsequent calls to `engine.get_inventory_cache()` SHALL return this cached grid

#### Scenario: Inventory service unavailable
- **WHEN** the inventory service is unreachable (connection error or non-200 response)
- **THEN** the cache SHALL retain its previous value (or `None` if never populated)
- **AND** the poller SHALL NOT raise an exception or stop the background task
- **AND** `get_cache()` SHALL return `{"grid": null, "rows": 0, "cols": 0}` when no data has been fetched

#### Scenario: Cache refreshes after transient failure
- **WHEN** the inventory service becomes reachable again after a failure
- **THEN** the next 3-second poll SHALL successfully update the cache

### Requirement: INVENTORY_URL configuration
The `InventoryPoller` SHALL accept the inventory service base URL as a constructor parameter, resolved from the `INVENTORY_URL` environment variable in `deps.py`, with a default value of `http://localhost:8103`.

#### Scenario: Default URL used in development
- **WHEN** `INVENTORY_URL` is not set
- **THEN** the poller SHALL connect to `http://localhost:8103/inventory`

#### Scenario: Custom URL used in containerized deployment
- **WHEN** `INVENTORY_URL` is set to `http://inventory:8103`
- **THEN** the poller SHALL connect to `http://inventory:8103/inventory`

## ADDED Requirements

### Requirement: InventoryPoller adapter interface
The `InventoryPoller` class in `adapters/inventory_poller.py` SHALL expose: `async start()` to begin polling, `async stop()` to cancel the background task, and `get_cache() -> dict[str, Any]` to read the current cached inventory.

#### Scenario: Start begins background polling
- **WHEN** `start()` is called
- **THEN** a background asyncio task SHALL begin polling the inventory endpoint every 3 seconds
- **AND** calling `start()` again while already running SHALL be a no-op

#### Scenario: Stop cancels background polling
- **WHEN** `stop()` is called
- **THEN** the background task SHALL be cancelled
- **AND** subsequent calls to `get_cache()` SHALL return the last cached value

#### Scenario: Adapter injected into SimulationEngine
- **WHEN** `SimulationEngine` is constructed in `deps.py`
- **THEN** it SHALL receive an `InventoryPoller` instance as a parameter
- **AND** `engine.get_inventory_cache()` SHALL delegate to `inventory_poller.get_cache()`

### Requirement: Lifespan management in api.py
The application lifespan in `api.py` SHALL start and stop the `InventoryPoller` adapter directly, following the same pattern as `KafkaObserver`.

#### Scenario: Poller starts during app startup
- **WHEN** the FastAPI application starts
- **THEN** `inventory_poller.start()` SHALL be called in the lifespan context manager

#### Scenario: Poller stops during app shutdown
- **WHEN** the FastAPI application shuts down
- **THEN** `inventory_poller.stop()` SHALL be called in the lifespan context manager
