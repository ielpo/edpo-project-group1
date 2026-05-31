## 1. Create InventoryPoller adapter

- [x] 1.1 Create `adapters/inventory_poller.py` with `InventoryPoller` class (start, stop, get_cache)
- [x] 1.2 Implement the background polling loop (httpx, 3-second interval, error handling)
- [x] 1.3 Add unit test for InventoryPoller (mock httpx, verify start/stop/cache behavior)

## 2. Wire into deps.py

- [x] 2.1 Instantiate `InventoryPoller` in `build_dependencies()` with `INVENTORY_URL` env var
- [x] 2.2 Pass `inventory_poller` into `SimulationEngine.__init__()` as a new parameter
- [x] 2.3 Add `inventory_poller` to the returned deps dict

## 3. Update SimulationEngine

- [x] 3.1 Add `inventory_poller` constructor parameter to `SimulationEngine.__init__()`
- [x] 3.2 Replace `get_inventory_cache()` body with delegation to `self._inventory_poller.get_cache()`
- [x] 3.3 Remove `start_inventory_poller`, `stop_inventory_poller`, `_inventory_poll_loop` methods
- [x] 3.4 Remove `_inventory_cache`, `_inventory_task`, `_inventory_url` instance variables
- [x] 3.5 Remove `httpx` import from engine.py

## 4. Update api.py lifespan

- [x] 4.1 Add `inventory_poller` to deps access in `create_app`
- [x] 4.2 Replace `engine.start_inventory_poller()` with `await inventory_poller.start()` in lifespan startup
- [x] 4.3 Replace `await engine.stop_inventory_poller()` with `await inventory_poller.stop()` in lifespan shutdown

## 5. Verify

- [x] 5.1 Run existing test suite to confirm no regressions
- [x] 5.2 Verify the service starts and the twin fragment shows inventory data
