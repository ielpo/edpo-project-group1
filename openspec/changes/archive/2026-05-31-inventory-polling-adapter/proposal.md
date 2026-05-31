## Why

The `SimulationEngine` currently owns an HTTP polling loop, an httpx client, a cache dict, and asyncio task management for inventory data — pure adapter-level I/O that leaks networking concerns into the domain module. This violates locality: inventory polling bugs are tangled with engine logic. The project already has an identical adapter pattern (`KafkaObserver`) that proves the seam works. Extracting the inventory poller now aligns the codebase and makes the engine testable without a running Inventory Service.

## What Changes

- Extract `start_inventory_poller`, `stop_inventory_poller`, `_inventory_poll_loop`, and `get_inventory_cache` from `engine.py` into a new `adapters/inventory_poller.py` module.
- The new `InventoryPoller` adapter follows the same start/stop lifecycle as `KafkaObserver`.
- `SimulationEngine` receives the poller as a dependency (injected via `deps.py`) and calls `.get_cache()` instead of managing the polling loop itself.
- `deps.py` wires the new adapter alongside existing adapters.
- Remove `httpx` usage from `engine.py` entirely.

## Capabilities

### New Capabilities
- `inventory-proxy`: Standalone adapter that polls the Inventory Service over HTTP and exposes a local cache for the simulated factory engine.

### Modified Capabilities

## Impact

- `services/simulated-factory/simulated_factory/engine.py` — removes ~40 lines (polling loop, cache, task management)
- `services/simulated-factory/simulated_factory/deps.py` — adds InventoryPoller instantiation and injection
- `services/simulated-factory/simulated_factory/adapters/inventory_poller.py` — new file
- `services/simulated-factory/simulated_factory/api.py` — lifespan hooks change from `engine.start_inventory_poller()` to `inventory_poller.start()`
- No API changes for external consumers; internal-only refactor.
