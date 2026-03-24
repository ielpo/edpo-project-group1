from uuid import UUID
from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional

app = FastAPI(title="Inventory Service")

ROWS = 5
COLS = 4
COLOURS = ["Red", "Green", "Blue", "Yellow"]  # one colour per column (y=0..3)

# Grid cell: None (empty) or {"colour": str, "reserved": bool, "order_id": str | None}
def default_grid() -> list[list[dict | None]]:
    return [
        [{"colour": COLOURS[y], "reserved": False, "order_id": None} for y in range(COLS)]
        for _ in range(ROWS)
    ]

grid: list[list[dict | None]] = default_grid()

# Tracks cells removed by /fetch, keyed by order_id → [{"x", "y", "colour"}]
fetch_log: dict[str, list[dict]] = {}


def grid_response(**extra) -> dict:
    return {"grid": grid, "rows": ROWS, "cols": COLS, **extra}


class PositionDto(BaseModel):
    x: int
    y: int
    colour: str


class ReserveInventoryDto(BaseModel):
    count: int
    colour: str


class RestoreRequest(BaseModel):
    orderId: Optional[str] = None


@app.get("/inventory")
def get_inventory():
    return grid_response()


@app.post("/reserve/{orderId}", status_code=200)
def reserve_inventory(orderId: UUID, req: ReserveInventoryDto):
    order_id = str(orderId)
    colour = req.colour.capitalize()

    if colour not in COLOURS:
        return JSONResponse(
            status_code=400,
            content={"message": f"Unknown color: {req.colour}. Valid colors: {COLOURS}"},
        )

    already_reserved = any(
        grid[x][y] is not None and grid[x][y].get("order_id") == order_id
        for x in range(ROWS)
        for y in range(COLS)
    )
    if already_reserved or order_id in fetch_log:
        return JSONResponse(
            status_code=409,
            content={"message": f"Order '{order_id}' already has reserved blocks"},
        )

    available = [
        (x, y)
        for x in range(ROWS)
        for y in range(COLS)
        if grid[x][y] is not None
        and grid[x][y]["colour"] == colour
        and not grid[x][y]["reserved"]
    ]

    if len(available) < req.count:
        raise HTTPException(
            status_code=409,
            detail=f"Not enough {colour} blocks. Requested: {req.count}, available: {len(available)}",
        )

    for x, y in available[: req.count]:
        grid[x][y]["reserved"] = True
        grid[x][y]["order_id"] = order_id

    return Response(status_code=200)


@app.get("/reserve/{orderId}")
def get_reserved_positions(orderId: UUID):
    order_id = str(orderId)
    positions = [
        PositionDto(x=x, y=y, colour=grid[x][y]["colour"]).model_dump()
        for x in range(ROWS)
        for y in range(COLS)
        if grid[x][y] is not None and grid[x][y].get("order_id") == order_id
    ]

    if not positions:
        raise HTTPException(status_code=404, detail=f"No reservations found for order '{order_id}'")

    return {"positions": positions}


@app.post("/fetch/{orderId}")
def fetch_inventory(orderId: UUID):
    order_id = str(orderId)
    reserved = [
        (x, y)
        for x in range(ROWS)
        for y in range(COLS)
        if grid[x][y] is not None and grid[x][y].get("order_id") == order_id
    ]

    if not reserved:
        raise HTTPException(status_code=404, detail=f"No reserved blocks found for order '{order_id}'")

    fetched = []
    for x, y in reserved:
        colour = grid[x][y]["colour"]
        fetch_log.setdefault(order_id, []).append({"x": x, "y": y, "colour": colour})
        grid[x][y] = None
        fetched.append(PositionDto(x=x, y=y, colour=colour).model_dump())

    return grid_response(fetched=fetched)


@app.post("/restore")
def restore_inventory(req: RestoreRequest = RestoreRequest()):
    global grid

    if req.orderId is None:
        grid = default_grid()
        fetch_log.clear()
        return grid_response(message="Inventory restored to default state")

    order_id = req.orderId
    restored = []

    for x in range(ROWS):
        for y in range(COLS):
            cell = grid[x][y]
            if cell is not None and cell.get("order_id") == order_id:
                cell["reserved"] = False
                cell["order_id"] = None
                restored.append(PositionDto(x=x, y=y, colour=cell["colour"]).model_dump())

    for entry in fetch_log.pop(order_id, []):
        x, y, colour = entry["x"], entry["y"], entry["colour"]
        grid[x][y] = {"colour": colour, "reserved": False, "order_id": None}
        restored.append(PositionDto(x=x, y=y, colour=colour).model_dump())

    if not restored:
        raise HTTPException(status_code=404, detail=f"No blocks found for order '{order_id}'")

    return grid_response(message=f"Restored {len(restored)} block(s) for order '{order_id}'", restored=restored)


app.mount("/", StaticFiles(directory="static", html=True), name="static")
