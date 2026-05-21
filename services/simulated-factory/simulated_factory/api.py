from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.encoders import jsonable_encoder
from fastapi.responses import HTMLResponse, JSONResponse

from simulated_factory.adapters.distance_publisher import DistancePublisher
from simulated_factory.engine import SimulationEngine
from simulated_factory.events import EventBridge, EventStore
from simulated_factory.models import RunPresetRequest, SensorUpdateRequest, utc_now


def create_app(config_path: str) -> FastAPI:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    logger = logging.getLogger(__name__)

    event_store = EventStore()
    event_bridge = EventBridge(
        mode=os.getenv("SIMULATOR_EVENT_BRIDGE", "none"),
        target_url=os.getenv("SIMULATOR_EVENT_BRIDGE_URL"),
        logger=logger,
    )
    distance_publisher = DistancePublisher(
        broker_url=os.getenv("SIMULATOR_BROKER_URL"),
        event_store=event_store,
        logger=logger,
    )
    engine = SimulationEngine(
        config_path=config_path,
        event_store=event_store,
        distance_publisher=distance_publisher,
        event_bridge=event_bridge,
    )

    app = FastAPI(title="Simulated Factory Service", version="1.0.0")
    app.state.engine = engine
    app.state.event_store = event_store

    @app.middleware("http")
    async def capture_requests(request: Request, call_next):
        body_bytes = await request.body()
        response = await call_next(request)

        if request.url.path != "/health":
            body: Any = None
            if body_bytes:
                try:
                    body = json.loads(body_bytes.decode("utf-8"))
                except json.JSONDecodeError:
                    body = body_bytes.decode("utf-8", errors="ignore")

            await event_store.append(
                "REST",
                source="http",
                message="Incoming simulator request",
                endpoint=request.url.path,
                method=request.method,
                status_code=response.status_code,
                payload={
                    "query": dict(request.query_params),
                    "body": body,
                },
            )

        return response

    @app.get("/", response_class=HTMLResponse)
    async def index() -> str:
        return _ui_html()

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/status")
    async def get_status() -> JSONResponse:
        return JSONResponse(jsonable_encoder(engine.get_status()))

    @app.get("/api/presets")
    async def list_presets() -> dict[str, Any]:
        return {"items": engine.list_presets()}

    @app.post("/api/presets/run", status_code=202)
    @app.post("/api/simulations/run", status_code=202)
    async def run_preset(request_body: RunPresetRequest) -> dict[str, str]:
        try:
            run_id = await engine.run_preset(request_body.preset, request_body.speed)
        except KeyError:
            raise HTTPException(status_code=404, detail=f"Unknown preset {request_body.preset}")
        except RuntimeError as exc:
            raise HTTPException(status_code=409, detail=str(exc))
        return {"runId": run_id, "status": "accepted"}

    @app.post("/api/presets/stop")
    @app.post("/api/simulations/stop")
    async def stop_preset() -> dict[str, str]:
        await engine.stop()
        return {"status": "stopping"}

    @app.post("/api/presets/reset")
    @app.post("/api/simulations/reset")
    async def reset_preset() -> dict[str, str]:
        await engine.reset()
        return {"status": "reset"}

    @app.get("/api/config/sensors")
    async def list_sensor_configs() -> JSONResponse:
        return JSONResponse(jsonable_encoder(engine.get_sensor_configs()))

    @app.put("/api/config/sensors/{sensor_id}")
    async def update_sensor(sensor_id: str, request_body: SensorUpdateRequest) -> JSONResponse:
        sensor = await engine.update_sensor(sensor_id, request_body)
        return JSONResponse(jsonable_encoder(sensor))

    @app.get("/api/events")
    async def list_events(
        page: int = 1,
        pageSize: int = 50,
        filter: str | None = None,
    ) -> dict[str, Any]:
        items, next_page = event_store.list_events(page=page, page_size=pageSize, filter_text=filter)
        return {"items": items, "nextPage": next_page}

    @app.post("/api/events", status_code=202)
    async def accept_event(payload: Any) -> dict[str, str]:
        await engine.record_external_event(payload)
        return {"status": "accepted"}

    @app.post("/api/dobot/{name}/commands", status_code=202)
    async def dobot_commands(name: str, payload: Any) -> dict[str, str]:
        correlation_id = await engine.handle_dobot_commands(name, payload)
        return {"correlationId": correlation_id}

    @app.get("/api/dobot/{name}/color")
    async def read_dobot_color(name: str) -> dict[str, Any]:
        color, raw_color = engine.read_color(name)
        return {
            "color": color,
            "raw_color": raw_color,
            "timestamp": utc_now().isoformat(),
        }

    @app.get("/api/dobot/{name}/ir")
    async def read_dobot_ir(name: str) -> dict[str, bool]:
        return {"ir": engine.read_ir(name)}

    @app.get("/api/dobot/{name}/state")
    async def read_dobot_state(name: str) -> JSONResponse:
        return JSONResponse(jsonable_encoder(engine.get_dobot_state(name)))

    @app.get("/color")
    @app.get("/api/color")
    async def read_color_sensor() -> dict[str, int]:
        return engine.read_color_sensor_bytes()

    @app.get("/read-color")
    async def read_color_alias() -> dict[str, Any]:
        color, raw_color = engine.read_color("left")
        return {"color": color, "raw_color": raw_color}

    @app.get("/read-ir")
    async def read_ir_alias() -> dict[str, bool]:
        return {"ir": engine.read_ir("left")}

    @app.websocket("/ws/status")
    async def websocket_status(websocket: WebSocket) -> None:
        await websocket.accept()
        queue = event_store.subscribe()
        await websocket.send_json(
            {
                "type": "state_snapshot",
                "state": jsonable_encoder(engine.get_status()),
            }
        )
        try:
            while True:
                event = await queue.get()
                await websocket.send_json(
                    {
                        "type": "event",
                        "event": event,
                        "state": jsonable_encoder(engine.get_status()),
                    }
                )
        except WebSocketDisconnect:
            return
        finally:
            event_store.unsubscribe(queue)

    return app


def _ui_html() -> str:
    web_path = Path(__file__).resolve().parents[1] / "web" / "index.html"
    return web_path.read_text(encoding="utf-8")