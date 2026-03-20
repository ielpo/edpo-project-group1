from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional

app = FastAPI(title="Inventory Service")

COLORS = ["red", "yellow", "blue", "green"]
GRID_SIZE = 4

# State: each color has 4 slots, True = available
inventory: dict[str, list[bool]] = {
    color: [True] * GRID_SIZE for color in COLORS
}


class TakeRequest(BaseModel):
    color: str
    count: int


class RestoreRequest(BaseModel):
    color: Optional[str] = None  # None means restore all


@app.get("/inventory")
def get_inventory():
    return {
        color: {"slots": slots, "available": sum(slots)}
        for color, slots in inventory.items()
    }


@app.post("/take")
def take_cubes(req: TakeRequest):
    color = req.color.lower()
    if color not in inventory:
        raise HTTPException(status_code=400, detail=f"Unknown color: {color}. Valid colors: {COLORS}")

    slots = inventory[color]
    available = sum(slots)

    if req.count <= 0:
        raise HTTPException(status_code=400, detail="Count must be greater than 0")

    if available < req.count:
        raise HTTPException(
            status_code=409,
            detail=f"Not enough {color} cubes. Requested: {req.count}, available: {available}"
        )

    taken = 0
    for i in range(GRID_SIZE - 1, -1, -1):
        if slots[i] and taken < req.count:
            slots[i] = False
            taken += 1

    return {
        "message": f"Took {taken} {color} cube(s)",
        "color": color,
        "taken": taken,
        "remaining": sum(slots),
        "inventory": {c: {"slots": s, "available": sum(s)} for c, s in inventory.items()},
    }


@app.post("/restore")
def restore_cubes(req: RestoreRequest = RestoreRequest()):
    if req.color is not None:
        color = req.color.lower()
        if color not in inventory:
            raise HTTPException(status_code=400, detail=f"Unknown color: {color}. Valid colors: {COLORS}")
        inventory[color] = [True] * GRID_SIZE
        restored = [color]
    else:
        for color in COLORS:
            inventory[color] = [True] * GRID_SIZE
        restored = COLORS

    return {
        "message": f"Restored: {', '.join(restored)}",
        "inventory": {c: {"slots": s, "available": sum(s)} for c, s in inventory.items()},
    }


app.mount("/", StaticFiles(directory="static", html=True), name="static")
