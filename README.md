# Event-driven and Process-oriented Architectures - Group 1
This repository contains all code related to the project and assignments.

# Project Description
The project simulates a factory that produces custom furniture on order.
The customer can select a type of furniture (chair, table, shelf, closet) and a color, the factory then fetches the components from inventory and assembles them using the robot arms.
Besides the Inventory Service, the system includes an Order Service, a Factory Service, and a Customer Service for status updates.
Communication with the Inventory Service uses HTTP/REST APIs, while communication between the other services is event-driven via Kafka.

# Development
For development a separate Docker compose configuration is available, this enables the simulation mode for services with device drivers.
The Spring Boot _local_ configuration must be used.

Docker compose `docker-compose-development.yml`

| Service             | URL            |
|---------------------|----------------| 
| Dashboard           | localhost:8100 |
| Order               | localhost:8101 |
| Factory             | localhost:8102 |
| Inventory           | localhost:8103 |
| Dobot Control Right | localhost:8200 |
| Dobot Control Left  | localhost:8201 |
| Color Sensor        | localhost:8202 |
| Simulated Factory   | localhost:8400 |
| Kafka Broker        | localhost:9092 |
| MQTT                | localhost:1883 |

## Running Application

1. Open the project in IntelliJ IDEA. The run configurations in `.run/` are available and can be used directly:
	- `Dashboard`
	- `Order`
	- `FactoryDevelopment` (uses the `local` Spring profile)

2. Start the development dependencies and simulated device services:

```bash
docker compose -f docker-compose-development.yml up --build -d
```
To start only the simulated factory and the services it depends on (for development), run:

```bash
docker compose -f docker-compose-development.yml up --build simulated-factory dobot-control mqtt
```

Open the simulated factory UI at `http://localhost:8400/`.

3. Start the Spring services from IntelliJ using the run configurations above.

4. To stop the development stack:

```bash
docker compose -f docker-compose-development.yml down
```

# Deployment
Docker compose `docker-compose.yml`

| Service             | URL               |
|---------------------|-------------------|
| Dashboard           | localhost:8100    | 
| Order               | localhost:8101    |
| Factory             | localhost:8102    |
| Inventory           | localhost:8103    |
| Dobot Control Right | localhost:8200    |
| Dobot Control Left  | localhost:8201    |
| Color Sensor        | 192.168.0.120:80  |
| Kafka Broker        | localhost:9092    |
| MQTT                | 192.168.0.21:1883 |

# Services

## Color Sensor Service
[services/color-sensor/README.md](services/color-sensor/README.md)

## Color Sensor Fake Service
[services/color-sensor-fake/README.md](services/color-sensor-fake/README.md)

## Dashboard Service
[services/dashboard/README.md](services/dashboard/README.md)

## Dobot Control Service
[services/dobot-control/README.md](services/dobot-control/README.md)

## Inventory Service
[services/inventory/README.md](services/inventory/README.md)
## Simulated Factory Service
[services/simulated-factory/README.md](services/simulated-factory/README.md)

# Data Structures
## Enums
### ItemType
| Value  | Description         |
|--------|---------------------|
| CHAIR  | 1 block             |
| TABLE  | 2 blocks horizontal |
| SHELF  | 2 blocks vertical   |
| CLOSET | 3 blocks vertical   |

### BlockColor
| Value  |
|--------|
| RED    |
| GREEN  |
| BLUE   |
| YELLOW |

## OrderDto
| Field    | Type          | Content                     |
|----------|---------------|-----------------------------|
| orderId  | string        | Order UUID                  |
| itemType | Enum.ItemType | Name of item to manufacture |

## ReserveInventoryDto
| Field   | Type            | Content                     |
|---------|-----------------|-----------------------------|
| orderId | string          | Order UUID                  |
| count   | int             | Number of blocks to reserve |
| color   | Enum.BlockColor | Color of blocks to reserve  |

## InventoryPositionDto
| Field | Type            | Content                        |
|-------|-----------------|--------------------------------|
| x     | int             | X coordinate of inventory grid |
| y     | int             | Y coordinate of inventory grid |
| color | Enum.BlockColor | Color of block                 |

### FetchInventoryDto
| Field     | Type                       | Content                                  |
|-----------|----------------------------|------------------------------------------|
| positions | List<InventoryPositionDto> | List of positions to take from inventory |

# Kafka Topics
Customer service subscribes to all topics and displays live information from the received events.

## Error
Error messages, feedback from Factory to Order service:
`error.v1`

| Field         | Type   | Content                                                 |
|---------------|--------|---------------------------------------------------------|
| message       | string | Message for user                                        |
| orderId       | string | Order ID                                                |
| correlationId | string | UUID to correlate message, not used by Customer service |

## Info
Information messages, Customer service subscribes to this:
`info.v1`

| Field         | Type   | Content                                                 |
|---------------|--------|---------------------------------------------------------|
| message       | string | Message for user                                        |
| orderId       | string | Order ID                                                |
| correlationId | string | UUID to correlate message, not used by Customer service |

## Order
`order.manufacture.v1`: command from Order to Factory service:

| Field         | Type      | Content                   |
|---------------|-----------|---------------------------|
| order         | OrderDto  | Order to be manufactured  |
| correlationId | string    | UUID to correlate message |

`order.complete.v1`: feedback from Factory to Order service:

| Field         | Type    | Content                      |
|---------------|---------|------------------------------|
| orderId       | string  | Order that was manufactured  |
| correlationId | string  | UUID to correlate message    |
