# Inventory Service

A FastAPI service managing a 5x4 inventory grid of colored blocks.

## Running the Service

```bash
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

The UI is available at `http://localhost:8000`.

## API

### Get Inventory
`GET /inventory`

Returns the full grid state.

```bash
curl http://localhost:8000/inventory
```

---

### Reserve Blocks
`POST /reserve/{orderId}`

Reserves a number of blocks of a given color for an order.

```bash
curl -X POST "http://localhost:8000/reserve/550e8400-e29b-41d4-a716-446655440000" -H "Content-Type: application/json" -d '{"count": 2, "color": "RED"}'
```

**Request body**
| Field | Type | Values |
|-------|------|--------|
| count | int  | Number of blocks to reserve |
| color | string | `RED`, `GREEN`, `BLUE`, `YELLOW` |

**Responses**
- `200` — blocks reserved
- `400` — unknown color
- `409` — not enough blocks available, or order already reserved

---

### Get Reserved Positions
`GET /reserve/{orderId}`

Returns the grid positions reserved for an order.

```bash
curl http://localhost:8000/reserve/550e8400-e29b-41d4-a716-446655440000
```

**Response: 200**
```json
{
  "positions": [
    { "x": 0, "y": 0, "color": "RED" },
    { "x": 1, "y": 0, "color": "RED" }
  ]
}
```

- `404` — no reservations found for this order

---

### Fetch Reserved Blocks
`POST /fetch/{orderId}`

Removes the reserved blocks from the grid (used when manufacturing starts).

```bash
curl -X POST http://localhost:8000/fetch/550e8400-e29b-41d4-a716-446655440000
```

**Responses**
- `200` — returns updated grid and list of fetched positions
- `404` — no reserved blocks found for this order

---

### Restore Inventory
`POST /restore`

Restores blocks for a specific order or resets the entire grid.

**Restore a specific order:**
```bash
curl -X POST http://localhost:8000/restore -H "Content-Type: application/json" -d '{"orderId": "550e8400-e29b-41d4-a716-446655440000"}'
```

**Reset entire grid:**
```bash
curl -X POST http://localhost:8000/restore -H "Content-Type: application/json" -d '{}'
```

- `200` — inventory restored
- `404` — no blocks found for the given order
