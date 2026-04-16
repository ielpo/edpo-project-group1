# Inventory Service

A FastAPI service managing a 5x4 inventory grid of colored blocks.

## Inventory Model
The inventory is represented by a grid. Each cell can either contain a block of a certain color, or be empty.
Additionally, occupied cells can be reserved for an order and are then not available for further orders.

Example of inventory grid state:
```
+---+---+---+---+
| R |   |   |   |
+---+---+---+---+
| R |   |   | Y |
+---+---+---+---+
| R |   |   | Y |
+---+---+---+---+
| R | G |   | Y |
+---+---+---+---+
| R | G | B | Y |
+---+---+---+---+
```

X coordinate represents row, top to bottom.
Y coordinate represents column, left to right.

Coordinates on grid `(x, y)`:
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

## Development
Install all required dependencies and create a virtual environment by running
```bash
cd services/inventory
uv sync
```

Run the service with
```bash
uv run uvicorn main:app
```

## API
Base URL: `http://localhost:8103`

### Get Inventory
`GET /inventory`

Returns the full grid state.

```bash
curl http://localhost:8103/inventory
```

---

### Reserve Blocks
`POST /reserve`

Reserves a number of blocks of a given color for an order.

```bash
curl -X POST "http://localhost:8103/reserve" -H "Content-Type: application/json" -d '{"orderId": "550e8400-e29b-41d4-a716-446655440000", "count": 2, "color": "RED"}'
```

**Request body**
Content is `ReserveInventoryDto`.

**Responses**
- `200`: blocks reserved for this `orderId`, no body
- `400`: request is invalid
- `409`: not enough free blocks of the requested color

Example `400`:
```json
{
  "message": "Unknown color: purple. Valid colors: ['RED', 'GREEN', 'BLUE', 'YELLOW']"
}
```

Example `409`:
```json
{
  "detail": "Not enough yellow blocks. Requested: 3, available: 2"
}
```

---

### Get Reserved Positions
`GET /reserve?orderId=UUID`

Returns the grid positions reserved for an order.

```bash
curl "http://localhost:8103/reserve?orderId=550e8400-e29b-41d4-a716-446655440000"
```

**Response: 200**
Returns `FetchInventoryDto`.

```json
{
  "positions": [
    { "x": 0, "y": 0, "color": "RED" },
    { "x": 1, "y": 0, "color": "RED" }
  ]
}
```

- `404`: the requested `orderId` is not known (might not have been reserved)

---

### Fetch Reserved Blocks
`POST /fetch?orderId=UUID`

Removes the reserved blocks from the grid (used when manufacturing starts).

```bash
curl -X POST "http://localhost:8103/fetch?orderId=550e8400-e29b-41d4-a716-446655440000"
```

**Responses**
- `200`: returns updated grid and list of fetched positions
- `404`: no reserved blocks found for this order

---

### Restore Inventory
`POST /restore`

Restores blocks for a specific order or resets the entire grid.

**Restore a specific order:**
```bash
curl -X POST "http://localhost:8103/restore" -H "Content-Type: application/json" -d '{"orderId": "550e8400-e29b-41d4-a716-446655440000"}'
```

**Reset entire grid:**
```bash
curl -X POST "http://localhost:8103/restore" -H "Content-Type: application/json" -d '{}'
```

- `200`: inventory restored
- `404`: no blocks found for the given order

## Data Structures

### BlockColor
| Value  |
|--------|
| RED    |
| GREEN  |
| BLUE   |
| YELLOW |

### ReserveInventoryDto
| Field   | Type            | Content                     |
|---------|-----------------|-----------------------------|
| orderId | string          | Order UUID                  |
| count   | int             | Number of blocks to reserve |
| color   | Enum.BlockColor | Color of blocks to reserve  |

### InventoryPositionDto
| Field | Type            | Content                        |
|-------|-----------------|--------------------------------|
| x     | int             | X coordinate of inventory grid |
| y     | int             | Y coordinate of inventory grid |
| color | Enum.BlockColor | Color of block                 |

### FetchInventoryDto
| Field     | Type                       | Content                                  |
|-----------|----------------------------|------------------------------------------|
| positions | List<InventoryPositionDto> | List of positions to take from inventory |
