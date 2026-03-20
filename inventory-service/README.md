# Inventory Service

A simple Python-based inventory service for the factory. Manages a 4x4 grid of colored cubes — each row represents a color (red, yellow, blue, green) and each column represents one cube slot.

## Setup

```bash
cd inventory-service
pip install -r requirements.txt
uvicorn main:app --reload
```

The service will be available at `http://localhost:8000`.

## UI

Open `http://localhost:8000` in your browser to see the current inventory state as a 4x4 colored grid. You can take and restore cubes directly from the UI.

## API

### GET /inventory

Returns the current state of the inventory.

**Terminal**
```bash
curl http://localhost:8000/inventory
```

**Response**
```json
{
  "red":    { "slots": [true, true, true, true], "available": 4 },
  "yellow": { "slots": [true, true, false, false], "available": 2 },
  "blue":   { "slots": [true, true, true, true], "available": 4 },
  "green":  { "slots": [true, true, true, true], "available": 4 }
}
```

---

### POST /take

Take a number of cubes of a given color. Cubes are removed from right to left.

**Terminal**
```bash
curl -X POST http://localhost:8000/take \
  -H "Content-Type: application/json" \
  -d '{"color": "yellow", "count": 2}'
```

**Request body**
```json
{
  "color": "yellow",
  "count": 2
}
```

**Response (success — 200)**
```json
{
  "message": "Took 2 yellow cube(s)",
  "color": "yellow",
  "taken": 2,
  "remaining": 2,
  "inventory": { ... }
}
```

**Response (not enough cubes — 409)**
```json
{
  "detail": "Not enough yellow cubes. Requested: 3, available: 2"
}
```

**Response (unknown color — 400)**
```json
{
  "detail": "Unknown color: purple. Valid colors: ['red', 'yellow', 'blue', 'green']"
}
```

---

### POST /restore

Restore cubes back to the inventory. Omit `color` (or pass `null`) to restore all colors.

**Terminal — restore all**
```bash
curl -X POST http://localhost:8000/restore \
  -H "Content-Type: application/json" \
  -d '{}'
```

**Terminal — restore a specific color**
```bash
curl -X POST http://localhost:8000/restore \
  -H "Content-Type: application/json" \
  -d '{"color": "yellow"}'
```

**Restore all colors**
```json
{}
```

**Restore a specific color**
```json
{
  "color": "yellow"
}
```

**Response (200)**
```json
{
  "message": "Restored: yellow",
  "inventory": { ... }
}
```

## Inventory Layout

```
         [1]   [2]   [3]   [4]
red      [ ]   [ ]   [ ]   [ ]
yellow   [ ]   [ ]   [ ]   [ ]
blue     [ ]   [ ]   [ ]   [ ]
green    [ ]   [ ]   [ ]   [ ]
```

- Filled cell = cube available
- Empty cell = cube taken
- When taking, cubes are removed from right to left (slot 4 → 1)
- When restoring, all slots for the selected color(s) are refilled
