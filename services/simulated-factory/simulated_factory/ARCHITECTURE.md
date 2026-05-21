# Simulated Factory — Architecture

## Overview

The **Simulated Factory** is a FastAPI-based service that emulates a physical factory with dobot robots, conveyor belts, and sensors. It executes scripted presets (step sequences), exposes a REST/SSE API for dashboards and orchestrators, and integrates with Kafka and MQTT for event-driven communication.

---

## Component Diagram

```mermaid
graph TB
    subgraph External
        Kafka[Kafka Broker]
        MQTT[MQTT Broker]
        Inventory[Inventory Service]
        Dashboard[Dashboard / HTMX UI]
        Orchestrator[Dobot Control / Orchestrator]
    end

    subgraph SimulatedFactory["Simulated Factory Service"]
        subgraph API["API Layer (FastAPI)"]
            REST[REST Endpoints]
            SSE[SSE Live Stream]
            Fragments[HTMX Fragments]
            Middleware[Request Capture Middleware]
        end

        subgraph Engine["Engine (Core Domain)"]
            Facade[SimulationEngine Facade]
            ProcessRunner[ProcessRunner]
            ControlPointMgr[ControlPointManager]
            ResourceMgr[ResourceManager]
            Runtime[SimulationRuntime]
        end

        subgraph Sensors["Sensor Plugin System"]
            BaseSensorABC[BaseSensor ABC]
            ColorSensor[ColorSensor]
            IrSensor[IrSensor]
            DistanceSensorPlugin[DistanceSensor]
            GenericSensor[GenericSensor]
            DobotColorSensor[DobotColorSensor]
            SensorLoader[SensorLoader]
        end

        subgraph Adapters["Adapters (Infrastructure)"]
            DistPub[DistancePublisher]
            KafkaObs[KafkaObserver]
            MqttPub[MqttPublisher]
        end

        subgraph Events["Event Infrastructure"]
            EventStore[EventStore]
            EventBridge[EventBridge]
        end
    end

    Dashboard -->|HTTP/SSE| API
    Orchestrator -->|REST commands| REST
    REST --> Middleware
    Middleware --> Facade
    Facade --> ProcessRunner
    Facade --> ControlPointMgr
    Facade --> ResourceMgr
    ProcessRunner --> Runtime
    ControlPointMgr --> Runtime
    ResourceMgr --> Runtime
    ResourceMgr --> Sensors
    ProcessRunner --> EventStore
    ControlPointMgr --> EventStore
    ResourceMgr --> EventStore
    ProcessRunner --> DistPub
    DistPub -->|MQTT publish| MQTT
    KafkaObs -->|consume topics| Kafka
    KafkaObs --> EventStore
    EventBridge -->|HTTP callback| External
    EventStore --> SSE
    ResourceMgr -->|poll inventory| Inventory
    MqttPub -->|MQTT publish| MQTT
```

---

## Runtime State Diagram

```mermaid
graph LR
    subgraph SimulationRuntime
        FS[FactoryState]
        PS[ProcessState]
        CS[ControlState]
        PR[PhysicalResources]
    end

    FS --- |run lifecycle| PS
    PS --- |step gates| CS
    CS --- |sensor access| PR
```

---

## Class Diagram — Engine

```mermaid
classDiagram
    class SimulationEngine {
        +event_store: EventStore
        +distance_publisher: DistancePublisher
        +event_bridge: EventBridge
        -_runtime: SimulationRuntime
        -_resource_mgr: ResourceManager
        -_process_runner: ProcessRunner
        -_control_mgr: ControlPointManager
        +get_status() SimulationState
        +list_presets() list
        +run_preset(preset_name, speed) str
        +stop()
        +reset()
        +fire_gate_if_matches(method, path) bool
        +get_sensor_configs() list
        +get_inventory_cache() dict
        +get_pending_actions() list
        +start_inventory_poller()
        +stop_inventory_poller()
    }

    class SimulationRuntime {
        +factory: FactoryState
        +process: ProcessState
        +control: ControlState
        +resources: PhysicalResources
        +reset()
    }

    class FactoryState {
        +run_id: str
        +status: SimulationStatus
        +current_preset: str?
        +run_counter: int
        +stop_requested: bool
        +run_task: Task?
        +lock: asyncio.Lock
    }

    class ProcessState {
        +current_step: int
        +current_step_name: str?
        +presets: dict~str, PresetDefinition~
    }

    class ControlState {
        +step_gate: tuple?
        +waiting_for_request: AwaitRequest?
        +interactive_config: InteractiveConfig
        +pending: dict~str, PendingAction~
        +pending_counter: int
    }

    class PhysicalResources {
        +default_sensors: dict~str, BaseSensor~
        +sensors: dict~str, BaseSensor~
        +dobots: dict~str, DobotRuntimeState~
        +inventory_cache: dict?
        +inventory_poll_task: Task?
    }

    class ProcessRunner {
        -_factory: FactoryState
        -_process: ProcessState
        -_control: ControlState
        -_resources: PhysicalResources
        -_event_store: EventStore
        -_distance_publisher: DistancePublisher
        +list_presets() list
        +run_preset(preset_name, speed) str
        -_execute_preset(preset, speed)
        -_await_step_gate(step, speed)
        -_apply_step_side_effects_sync(step)
        -_publish_distance_if_needed(step)
        -_clear_step_gate()
    }

    class ControlPointManager {
        -_factory: FactoryState
        -_process: ProcessState
        -_control: ControlState
        -_resources: PhysicalResources
        -_event_store: EventStore
        +fire_gate_if_matches(method, path)
        +matches_gate(method, path) bool
        +handle_dobot_commands(robot_name, payload) dict
        +resolve_pending_action(action_id, outcome, reason)
        -_apply_gate_side_effects(step)
        -_apply_commands(robot_name, command_list)
    }

    class ResourceManager {
        -_resources: PhysicalResources
        -_event_store: EventStore
        -_config_path: Path
        -_inventory_url: str
        +get_presets() dict
        +sensor_map_for_preset(preset) dict
        +get_sensor_configs() list~SensorConfig~
        +update_sensor(sensor_id, update) SensorConfig
        +read_color(robot_name) tuple
        +read_ir(robot_name) bool
        +make_plugin(sensor_id, config) BaseSensor
        -_load_config()
        -_make_plugin(sensor_id, config) BaseSensor
        -_infer_sensor_type(sensor_id, config) str
    }

    SimulationEngine *-- SimulationRuntime
    SimulationEngine *-- ProcessRunner
    SimulationEngine *-- ControlPointManager
    SimulationEngine *-- ResourceManager
    SimulationRuntime *-- FactoryState
    SimulationRuntime *-- ProcessState
    SimulationRuntime *-- ControlState
    SimulationRuntime *-- PhysicalResources
    ProcessRunner --> FactoryState
    ProcessRunner --> ProcessState
    ProcessRunner --> ControlState
    ProcessRunner --> PhysicalResources
    ControlPointManager --> FactoryState
    ControlPointManager --> ProcessState
    ControlPointManager --> ControlState
    ControlPointManager --> PhysicalResources
    ResourceManager --> PhysicalResources
```

---

## Class Diagram — Sensor Plugin System

```mermaid
classDiagram
    class BaseSensor {
        <<abstract>>
        +name: str
        #_cfg: SensorConfig
        +read()* Any
        +update(value)* 
        +to_dict()* dict
    }

    class MqttSensor {
        <<abstract>>
        +get_topic()* str
        +get_payload()* str
    }

    class ColorSensor {
        -_cfg: ColorSensorConfig
        +read(step?) tuple~str, list~
        +update(value)
        +to_dict() dict
        +to_sensor_config() ColorSensorConfig
        +clone() ColorSensor
        +apply_overrides(overrides)
        +apply_update_request(update)
    }

    class IrSensor {
        -_cfg: IrSensorConfig
        +read(step?) bool
        +update(value)
        +to_dict() dict
        +to_sensor_config() IrSensorConfig
        +clone() IrSensor
        +apply_overrides(overrides)
        +apply_update_request(update)
    }

    class DistanceSensor {
        -_cfg: DistanceSensorConfig
        -_message_id: int
        +read(step?) float
        +update(value)
        +get_topic() str
        +get_payload() str
        +to_dict() dict
        +to_sensor_config() DistanceSensorConfig
        +clone() DistanceSensor
        +apply_overrides(overrides)
        +apply_update_request(update)
    }

    class GenericSensor {
        +read(step?) Any
        +update(value)
    }

    class DobotColorSensor {
        -_cfg: DobotColorSensorConfig
        +read() tuple~str, list~
        +update(value)
    }

    class SensorConfig {
        +name: str
        +type: str
        +sensorId: str
    }

    class ColorSensorConfig {
        +mode: str
        +value: str?
        +raw_color: list~int~
        +scripted_values: list
    }

    class IrSensorConfig {
        +mode: str
        +value: Any
        +scripted_values: list
    }

    class DistanceSensorConfig {
        +mode: str
        +value: float?
        +mqtt_topic: str
        +message_type: str
        +uid: str
        +location: str
        +cadence_ms: int
    }

    BaseSensor <|-- ColorSensor
    BaseSensor <|-- IrSensor
    BaseSensor <|-- DistanceSensor
    BaseSensor <|-- GenericSensor
    BaseSensor <|-- DobotColorSensor
    MqttSensor <|.. DistanceSensor
    SensorConfig <|-- ColorSensorConfig
    SensorConfig <|-- IrSensorConfig
    SensorConfig <|-- DistanceSensorConfig
    BaseSensor --> SensorConfig : _cfg
```

---

## Class Diagram — Models (API / Domain)

```mermaid
classDiagram
    class SimulationStatus {
        <<enum>>
        IDLE
        RUNNING
        STOPPED
    }

    class SimulationState {
        +id: str
        +status: SimulationStatus
        +currentPreset: str?
        +currentStep: int
        +currentStepName: str?
        +timestamp: datetime
        +dobots: dict~str, DobotRuntimeState~
        +waitingForRequest: AwaitRequest?
    }

    class DobotRuntimeState {
        +position: Position
        +speed: float
        +acceleration: float
        +suction_enabled: bool
        +conveyor_speed: float
        +conveyor_distance: float
        +conveyor_direction: str
        +last_command: str?
    }

    class Position {
        +x: float
        +y: float
        +z: float
        +r: float
    }

    class PresetDefinition {
        +name: str
        +description: str
        +sensor_overrides: dict
        +steps: list~PresetStep~
    }

    class PresetStep {
        +name: str
        +delayMs: int
        +note: str?
        +publishDistance: float?
        +sensorUpdates: dict
        +awaitRequest: AwaitRequest?
    }

    class AwaitRequest {
        +method: str
        +path: str
    }

    class PendingAction {
        +id: str
        +robot_name: str
        +commands: list
        +correlation_id: str
        +created_at: datetime
        +outcome: str?
        +reason: str?
        +timed_out: bool
        +wait_for_resolution(timeout?) bool
        +resolve(outcome, reason?)
        +mark_timed_out()
        +to_public_dict() dict
    }

    class InteractiveConfig {
        +intercepted: set~str~
        +timeout_seconds: int
    }

    class EventEntry {
        +id: str
        +ts: datetime
        +type: str
        +source: str?
        +message: str?
        +topic: str?
        +endpoint: str?
        +method: str?
        +statusCode: int?
        +payload: Any
    }

    SimulationState --> SimulationStatus
    SimulationState --> DobotRuntimeState
    SimulationState --> AwaitRequest
    DobotRuntimeState --> Position
    PresetDefinition --> PresetStep
    PresetStep --> AwaitRequest
```

---

## Class Diagram — Adapters & Events

```mermaid
classDiagram
    class EventStore {
        -_events: deque~EventEntry~
        -_subscribers: set~Queue~
        -_subscriber_queue_size: int
        +append(event_type, ...)
        +subscribe() Queue
        +unsubscribe(queue)
        +list_events(page, page_size, filter_text, filter_mode) tuple
        +size() int
        +clear()
    }

    class EventBridge {
        -_mode: str
        -_target_url: str?
        -_logger: Logger
        +emit(event)
    }

    class DistancePublisher {
        -_broker_url: str?
        -_event_store: EventStore
        -_logger: Logger
        -_message_id: int
        +publish(sensor, distance)
        -_build_payload(sensor, distance) dict
    }

    class KafkaObserver {
        +event_store: EventStore
        +logger: Logger
        +bootstrap_servers: str
        +group_id: str
        +topics: tuple
        -_consumer: AIOKafkaConsumer?
        -_task: Task?
        -_running: bool
        +start()
        +stop()
        -_run()
    }

    class MqttPublisher {
        +hostname: str
        +port: int
        +event_store: EventStore
        +logger: Logger
        +publish(topic, payload)
    }

    DistancePublisher --> EventStore
    KafkaObserver --> EventStore
    MqttPublisher --> EventStore
    EventBridge ..> EventStore : optional relay
```

---

## Dependency Wiring

```mermaid
graph TD
    Main["main.py"] -->|create_app| API["api.py (FastAPI)"]
    API -->|build_dependencies| Deps["deps.py"]
    Deps --> ES[EventStore]
    Deps --> EB[EventBridge]
    Deps --> DP[DistancePublisher]
    Deps --> SE[SimulationEngine]
    Deps --> KO[KafkaObserver]

    SE --> RM[ResourceManager]
    SE --> PR[ProcessRunner]
    SE --> CM[ControlPointManager]
    SE --> RT[SimulationRuntime]

    RM -->|loads| Config["config.yml"]
    RM -->|instantiates| Sensors[Sensor Plugins]
    KO -->|consumes| Kafka[Kafka Topics]
    DP -->|publishes| MQTT[MQTT Broker]
```

---

## Simulation Lifecycle (State Machine)

```mermaid
stateDiagram-v2
    [*] --> IDLE
    IDLE --> RUNNING : run_preset()
    RUNNING --> IDLE : preset completed
    RUNNING --> STOPPED : stop() or cancel
    STOPPED --> IDLE : reset()
    IDLE --> IDLE : reset()
```

---

## Preset Execution Sequence

```mermaid
sequenceDiagram
    participant Client
    participant API
    participant Engine as SimulationEngine
    participant Runner as ProcessRunner
    participant Control as ControlPointManager
    participant Sensors
    participant EventStore
    participant MQTT

    Client->>API: POST /api/presets/run
    API->>Engine: run_preset(name, speed)
    Engine->>Runner: run_preset(name, speed)
    Runner->>EventStore: append(STATE, "Started preset")
    Runner->>Runner: create asyncio.Task(_execute_preset)

    loop For each PresetStep
        alt step has awaitRequest
            Runner->>Runner: set step_gate (Event + AwaitRequest)
            Note over Runner: Waits for matching HTTP request or timeout
            Client->>API: GET /api/dobot/{name}/color
            API->>Control: fire_gate_if_matches(method, path)
            Control->>Sensors: apply sensor updates
            Control->>Runner: signal Event
        else normal step
            Runner->>Sensors: apply sensorUpdates
            Runner->>MQTT: publish distance (if configured)
            Runner->>Runner: sleep(delayMs / speed)
        end
        Runner->>EventStore: append(STATE, step info)
    end

    Runner->>EventStore: append(STATE, "Preset completed")
    Runner-->>Engine: task done, status → IDLE
```

---

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **Facade pattern** (SimulationEngine) | Single entry point for API; delegates to focused sub-components |
| **Runtime dataclasses** vs Pydantic models | Mutable internal state (dataclass) separate from immutable API snapshots (Pydantic) |
| **Plugin-based sensors** | New sensor types added by dropping a module in `sensors/`; resolved by naming convention |
| **Request gating** | Steps can pause until a real HTTP request arrives, enabling realistic timing |
| **In-memory EventStore** | Bounded deque with pub/sub queues for real-time SSE without external dependencies |
| **Kafka Observer (read-only)** | Makes upstream process-topic activity visible in the UI without producing |
| **DistancePublisher via MQTT** | Emulates Tinkerforge-style distance messages consumed by downstream services |
