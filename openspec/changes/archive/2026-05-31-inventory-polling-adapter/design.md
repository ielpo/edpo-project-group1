## Context

The `SimulationEngine` in `services/simulated-factory/simulated_factory/engine.py` currently manages an HTTP polling loop that fetches inventory grid data from the Inventory Service (`GET /inventory`). This involves:

- An `httpx.AsyncClient` instantiated inside a long-running coroutine
- A `_inventory_cache` dict storing the last successful response
- An `asyncio.Task` with start/stop lifecycle methods
- A configurable `_inventory_url` resolved from env vars

The project already has `adapters/kafka_observer.py` — a read-only Kafka consumer with the same start/stop pattern. The inventory poller is functionally identical in shape: an async background task that produces data for the engine to read.

## Goals / Non-Goals

**Goals:**
- Extract inventory HTTP polling into `adapters/inventory_poller.py` with a clean start/stop/get_cache interface
- Inject the adapter into `SimulationEngine` via `deps.py`
- Make the engine testable without a running Inventory Service (swap in a fake adapter)
- Follow the existing `KafkaObserver` pattern for consistency

**Non-Goals:**
- Changing the polling strategy (interval, retry, backoff) — keep current 3-second interval
- Adding WebSocket or push-based updates from Inventory Service
- Modifying the Inventory Service API itself
- Changing how `api.py` uses `engine.get_inventory_cache()` — the engine still exposes this, it just delegates

## Decisions

### 1. Protocol: class with start/stop/get_cache

**Choice:** `InventoryPoller` class with `async start()`, `async stop()`, `get_cache() -> dict[str, Any]`.

**Rationale:** Mirrors `KafkaObserver` exactly. Both are background data sources wired in `deps.py` and managed in the app lifespan. No need for an abstract base class — one adapter justifies a hypothetical seam; if a second appears (e.g. WebSocket-based inventory updates) we formalize the protocol then.

**Alternative considered:** Abstract `InventorySource` ABC — rejected because only one implementation exists today. Two adapters justify a real seam; one is hypothetical.

### 2. Injection point: constructor parameter on SimulationEngine

**Choice:** Pass `inventory_poller` into `SimulationEngine.__init__()` alongside `mqtt_publisher` and `event_bridge`.

**Rationale:** Consistent with how other adapters are provided. Engine stores a reference and delegates `get_inventory_cache()` → `self._inventory_poller.get_cache()`.

### 3. Lifespan management: api.py controls start/stop

**Choice:** `api.py` lifespan calls `inventory_poller.start()` / `inventory_poller.stop()` directly (same as `kafka_observer.start()` / `kafka_observer.stop()`).

**Rationale:** The engine doesn't own adapter lifecycles for KafkaObserver, so it shouldn't for inventory either. `deps.py` builds the adapter; `api.py` manages its lifecycle.

### 4. Configuration: env var INVENTORY_URL, default http://localhost:8103

**Choice:** Keep existing env var (`INVENTORY_URL`) and default. Pass it as a constructor arg resolved in `deps.py`.

## Risks / Trade-offs

- **[Trivial interface duplication]** → `engine.get_inventory_cache()` becomes a one-liner delegation. Acceptable: it preserves the engine's role as single entry point for API handlers.
- **[Cache staleness during tests]** → Test adapter returns a fixed dict. If tests need dynamic inventory, the fake can be extended. Low risk.
- **[Polling continues when engine is idle]** → Current behavior. Unchanged. Could optimize later but out of scope.
