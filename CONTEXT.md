# Domain Context: Event-Driven Factory Simulation

## Overview

This system simulates a smart factory that manufactures custom furniture on demand. Customers order items (chairs, tables, shelves, closets) in a specified color, and the factory fetches components from inventory and assembles them using robotic arms.

## Key Concepts

### Order Types (ItemType)
- **CHAIR** — 1 block
- **TABLE** — 2 blocks (horizontal arrangement)
- **SHELF** — 2 blocks (vertical arrangement)
- **CLOSET** — 3 blocks (vertical arrangement)

### Block Colors
Available in four variants: RED, GREEN, BLUE, YELLOW.

## Services

### Core Services
- **Order Service** (`order`) — Orchestrates the manufacturing workflow via BPMN (Operaton)
- **Factory Service** (`factory`) — Executes assembly logic, controls robots and sensors
- **Inventory Service** (`inventory`) — Manages block stock; REST API
- **Dashboard Service** (`dashboard`) — Web UI for monitoring and customer updates
- **Customer Service** (`customer`) — Displays order status and notifications to users

### Device Control Services
- **Dobot Control Service** (`dobot-control`) — Manages robot arms (right and left)
- **Color Sensor Service** (`color-sensor`) — Reads block colors from physical sensor
- **Color Sensor Fake Service** (`color-sensor-fake`) — Simulated color sensor for development
- **Simulated Factory Service** (`simulated-factory`) — IoT device simulator for local development

## Communication Patterns

### Orchestration & Commands
- The **Order Service** orchestrates manufacturing via BPMN, encapsulated in Operaton
- Assembly logic is encapsulated in a single service task in the BPMN process
- The orchestrator sends **commands** to service tasks and awaits domain events

### Event-Driven Communication (Kafka)
- Services communicate via Kafka topics using domain events, not commands (except from orchestrator)
- The **Factory Service** emits events on order completion or failure
- The **Customer Service** subscribes to all events to provide real-time status updates
- Correlation IDs link asynchronous requests to responses across process boundaries

### Synchronous Communication (REST/HTTP)
- The **Inventory Service** uses HTTP/REST for block reservation and fetching
- Chosen for straightforward request-response semantics (no async state needed)

## Kafka Topics

| Topic | Direction | Content |
|-------|-----------|---------|
| `order.manufacture.v1` | Order → Factory | Command to manufacture (includes OrderDto and correlationId) |
| `order.complete.v1` | Factory → Order | Event: manufacturing succeeded |
| `error.v1` | Factory → Order/Customer | Event: manufacturing or system failure |
| `info.v1` | Any → Customer | Event: informational message (order status, etc.) |

## Data Structures

### OrderDto
- `orderId` (UUID string) — Unique order identifier
- `itemType` (Enum) — Type of furniture to manufacture

### ReserveInventoryDto
- `orderId` — Correlates with order
- `count` (int) — Number of blocks needed
- `color` (Enum) — Block color to reserve

### InventoryPositionDto
- `x`, `y` (int) — Grid coordinates in inventory
- `color` (Enum) — Block color at position

## Development Setup

- **Config**: Spring Boot `local` profile activates simulation mode
- **Services** run on localhost:810x (Dashboard 8100, Order 8101, Factory 8102, Inventory 8103)
- **Dobot Control** and **Color Sensor** simulators on localhost:820x
- **Simulated Factory** UI at localhost:8400
- **Kafka Broker** on localhost:9092
- **MQTT** on localhost:1883

See the main README for setup instructions.

## Key Decisions

- **Operaton as BPMN Engine** (ADR-3) — Chosen over Camunda 8 for on-prem IoT constraints and low concurrency
- **Commands & Events Pattern** (ADR-4) — Orchestrator sends commands; services emit events
- **Assembly as Single Service Task** (ADR-9) — All robot/sensor logic in one task for simplicity; no sub-process modeling
- **Kafka for Event Streaming** (ADR-7) — Chosen over direct HTTP for loose coupling and extensibility

See `doc/adr/` for full architectural decision records.
