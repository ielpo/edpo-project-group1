## Dashboard Service

The dashboard is a Spring Boot web application that provides a live UI for KAFKEA.

It shows:
- current inventory state (via the Inventory service REST API)
- inventory actions (reserve, fetch, restore)
- live order progress updates (via Kafka events pushed to the browser through WebSocket)

Default URL: `http://localhost:8100`

## Runtime Dependencies

- Java 21
- Maven
- Kafka broker on `localhost:9092`
- Inventory service on `http://localhost:8103`

The defaults are configured in `src/main/resources/application.yml`.

## Run Locally

From the repository root:

1. Start infrastructure/services used by dashboard (at least Kafka + Inventory):

```bash
docker compose up -d kafka inventory
```

2. Start the dashboard service:

```bash
cd services/dashboard
mvn spring-boot:run
```

3. Open the UI:

```text
http://localhost:8100
```

## Relevant Endpoints

- `GET /`: dashboard UI (`src/main/resources/static/index.html`)
- `GET /config.json`: frontend runtime config (inventory base URL)
- `WS /ws/events`: live event stream for order tracker
