# Simulated Factory Read Model

Version: v1

## Purpose

Define the read-model boundaries for the simulated-factory service: which module owns each piece of runtime state, how composed views are assembled, and what the engine interface exposes versus delegates.

## Requirements

### Requirement: Ownership-backed read routing
The simulated-factory HTTP module SHALL route read-only runtime queries to the module that owns the requested state instead of using engine pass-through methods.

Ownership for this capability is defined as:
- inventory cache -> `InventoryPoller`
- preset catalog and sensor configuration -> `SensorRegistry`
- dobot runtime state -> live `ActuatorRegistry`

#### Scenario: Inventory endpoint reads from inventory owner
- **WHEN** a client requests `GET /api/inventory`
- **THEN** the response is built from the `InventoryPoller` cache
- **AND** the engine is not required to expose an inventory-cache getter for that route

#### Scenario: Sensor config endpoint reads from sensor owner
- **WHEN** a client requests `GET /api/config/sensors`
- **THEN** the response is built from `SensorRegistry` live sensor configuration
- **AND** the engine is not required to expose a sensor-config getter for that route

#### Scenario: Dobot state endpoint reads from actuator owner
- **WHEN** a client requests `GET /api/dobot/{name}/state`
- **THEN** the response is built from the live dobot state owner
- **AND** the engine is not required to expose a dobot-state getter for that route

### Requirement: Shared runtime snapshot for UI updates
The simulator SHALL provide one runtime snapshot module that assembles the read model for fragment rendering and SSE updates from engine lifecycle state, event history, inventory cache, sensor configuration, and pending-action state.

#### Scenario: Fragment handlers share one snapshot source
- **WHEN** the HTTP module renders `status`, `presets`, `twin`, `events`, or `pending` fragments
- **THEN** each fragment's view model is assembled through the runtime snapshot module
- **AND** the HTTP module does not recompute those view models by manually calling unrelated getters in each route

#### Scenario: SSE uses the same snapshot source
- **WHEN** `GET /sse/status` emits the initial out-of-band render or a later update
- **THEN** the rendered HTML is assembled through the same runtime snapshot module used by fragment endpoints
- **AND** the selected event filter mode is applied consistently across fragment and SSE rendering

### Requirement: Engine lifecycle read boundary
The `SimulationEngine` SHALL keep read methods only for lifecycle state it owns directly and SHALL NOT re-expose ownership-backed state as dedicated pass-through methods.

Lifecycle-owned read state for this capability includes run status, current step, active gate, pending actions, and interactive configuration.

#### Scenario: Lifecycle reads remain on engine
- **WHEN** the HTTP module needs the current run status or pending actions
- **THEN** it reads that state from the engine lifecycle interface
- **AND** the engine remains the owner of those lifecycle semantics

#### Scenario: Ownership-backed pass-through methods are removed
- **WHEN** the read-model change is applied
- **THEN** the engine interface no longer includes dedicated pass-through methods for preset catalog, sensor configuration, dobot runtime state, or inventory cache
- **AND** callers use the state-owning modules or runtime snapshot module instead
