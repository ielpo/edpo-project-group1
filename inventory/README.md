# Inventory Service

A Python-based inventory service for the factory. Manages a 5×4 grid of coloured blocks — each cell can hold a block of a certain colour or be empty, and can be reserved for a specific order.

## Setup

```bash
cd inventory-service
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

The service will be available at `http://localhost:8000`.

## UI

Open `http://localhost:8000` in your browser to see the live grid state. The grid auto-refreshes every 3 seconds, so external API calls are reflected immediately. Reserved cells are marked with a dashed outline.

## Grid Layout

The inventory is a 5×4 grid addressed by `(x, y)` coordinates:
- `x` = row (0 = top, 4 = bottom)
- `y` = column (0 = left, 3 = right)

Each column holds one colour: y=0 → Red, y=1 → Green, y=2 → Blue, y=3 → Yellow.

```
+-----+-----+-----+-----+
| 0,0 | 0,1 | 0,2 | 0,3 |
+-----+-----+-----+-----+
| 1,0 | 1,1 | 1,2 | 1,3 |
+-----+-----+-----+-----+
| 2,0 | 2,1 | 2,2 | 2,3 |
+-----+-----+-----+-----+
| 3,0 | 3,1 | 3,2 | 3,3 |
+-----+-----+-----+-----+
| 4,0 | 4,1 | 4,2 | 4,3 |
+-----+-----+-----+-----+
```

Default state (all 5 slots per colour filled):
```
+---+---+---+---+
| R | G | B | Y |
+---+---+---+---+
| R | G | B | Y |
+---+---+---+---+
| R | G | B | Y |
+---+---+---+---+
| R | G | B | Y |
+---+---+---+---+
| R | G | B | Y |
+---+---+---+---+
```

Blocks are reserved from the top (x=0) downward.

## API

Base URL: `http://localhost:8000`

---

### GET /inventory

Returns the full grid state.

```bash
curl http://localhost:8000/inventory
```

**Response (200)**
```json
{
  "rows": 5,
  "cols": 4,
  "grid": [
    [
      {"colour": "Red",  "reserved": false, "order_id": null},
      {"colour": "Green","reserved": true,  "order_id": "abc-123"},
      {"colour": "Blue", "reserved": false, "order_id": null},
      {"colour": "Yellow","reserved": false,"order_id": null}
    ],
    "..."
  ]
}
```

Each cell is either `null` (empty) or `{"colour", "reserved", "order_id"}`.

---

### POST /reserve/{orderId}

Reserve a number of blocks of a given colour for an order. `orderId` must be a valid UUID. Returns `200` with no body on success.

```bash
curl -X POST http://localhost:8000/reserve/550e8400-e29b-41d4-a716-446655440000 \
  -H "Content-Type: application/json" \
  -d '{"count": 2, "colour": "Red"}'
```

**Request body — ReserveInventoryDto**
```json
{
  "count": 2,
  "colour": "Red"
}
```

**Response (200)** — no body

**Response (400 — unknown colour)**
```json
{
  "message": "Unknown color: purple. Valid colors: ['Red', 'Green', 'Blue', 'Yellow']"
}
```

**Response (409 — not enough blocks)**
```json
{
  "detail": "Not enough Red blocks. Requested: 3, available: 1"
}
```

**Response (409 — order already reserved)**
```json
{
  "message": "Order '550e8400-e29b-41d4-a716-446655440000' already has reserved blocks"
}
```

**Response (422 — invalid UUID)**
```json
{
  "detail": "value is not a valid uuid"
}
```

---

### GET /reserve/{orderId}

Returns the list of positions reserved for a given order — FetchInventoryDto.

```bash
curl http://localhost:8000/reserve/550e8400-e29b-41d4-a716-446655440000
```

**Response (200)**
```json
{
  "positions": [
    {"x": 0, "y": 0, "colour": "Red"},
    {"x": 1, "y": 0, "colour": "Red"}
  ]
}
```

**Response (404 — order not found)**
```json
{
  "detail": "No reservations found for order '550e8400-e29b-41d4-a716-446655440000'"
}
```

---

### POST /fetch/{orderId}

Remove all reserved blocks for a given order from the grid (called by the factory when manufacturing starts).

```bash
curl -X POST http://localhost:8000/fetch/550e8400-e29b-41d4-a716-446655440000
```

**Response (200)**
```json
{
  "rows": 5,
  "cols": 4,
  "fetched": [
    {"x": 0, "y": 0, "colour": "Red"},
    {"x": 1, "y": 0, "colour": "Red"}
  ],
  "grid": ["..."]
}
```

**Response (404 — no reserved blocks for order)**
```json
{
  "detail": "No reserved blocks found for order '550e8400-e29b-41d4-a716-446655440000'"
}
```

---

### POST /restore

Restore blocks for a specific order, or reset the entire grid.

Restoring by `orderId` handles both cases:
- Blocks still **reserved** → un-reserved and made available again
- Blocks already **fetched** → put back into their original positions

**Restore by order ID**
```bash
curl -X POST http://localhost:8000/restore \
  -H "Content-Type: application/json" \
  -d '{"orderId": "abc-123"}'
```

**Response (200)**
```json
{
  "message": "Restored 2 block(s) for order 'abc-123'",
  "restored": [
    {"x": 0, "y": 0, "colour": "Red"},
    {"x": 1, "y": 0, "colour": "Red"}
  ],
  "grid": ["..."]
}
```

**Response (404 — order not found)**
```json
{
  "detail": "No blocks found for order 'abc-123'"
}
```

**Reset entire grid**
```bash
curl -X POST http://localhost:8000/restore \
  -H "Content-Type: application/json" \
  -d '{}'
```

**Response (200)**
```json
{
  "message": "Inventory restored to default state",
  "grid": ["..."]
}
```
