import asyncio
import json
import logging
import re
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import (
    Body,
    FastAPI,
    HTTPException,
    Request,
)
from fastapi.encoders import jsonable_encoder
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.templating import Jinja2Templates

from simulated_factory.deps import build_dependencies
from simulated_factory.models import (
    RunPresetRequest,
    SensorUpdateRequest,
    SimulationStatus,
    TriggerEvent,
    utc_now,
)
from simulated_factory.runtime_snapshot import RuntimeSnapshot

from simulated_factory.utils import format_sse


TEMPLATES_DIR = Path(__file__).resolve().parents[1] / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


# Path patterns whose REST traffic is reclassified as a process-relevant
# SENSOR_REQUEST event so that the operator-focused view can include sensor reads.
_SENSOR_REQUEST_PATH_RE = re.compile(r"^/api/dobot/[^/]+/(?:color|ir)$")


def create_app(config_path: str) -> FastAPI:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
    )
    logger = logging.getLogger(__name__)

    deps = build_dependencies(config_path, logger=logger)
    event_store = deps["event_store"]
    engine = deps["engine"]
    sensor_registry = deps["sensor_registry"]
    actuator_registry = deps["actuator_registry"]
    inventory_poller = deps["inventory_poller"]
    kafka_observer = deps["kafka_observer"]

    snapshot = RuntimeSnapshot(
        engine=engine,
        sensor_registry=sensor_registry,
        actuator_registry=actuator_registry,
        inventory_poller=inventory_poller,
        event_store=event_store,
    )

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        await kafka_observer.start()
        await inventory_poller.start()
        try:
            yield
        finally:
            await inventory_poller.stop()
            await kafka_observer.stop()

    app = FastAPI(
        title="Simulated Factory Service",
        version="1.0.0",
        lifespan=lifespan,
    )
    app.state.engine = engine
    app.state.event_store = event_store
    app.state.kafka_observer = kafka_observer
    app.state.sensor_registry = sensor_registry
    app.state.actuator_registry = actuator_registry
    app.state.inventory_poller = inventory_poller
    app.state.runtime_snapshot = snapshot

    @app.middleware("http")
    async def capture_requests(request: Request, call_next):
        body_bytes = await request.body()

        if request.url.path != "/health":
            # Fire any active preset gate that matches this incoming request
            # BEFORE the handler runs so its sensor reads observe the updated
            # state. The unified try_fire_gate is a no-op when no HTTP gate is
            # active or the request does not match.
            try:
                engine.try_fire_gate(
                    TriggerEvent(
                        type="http",
                        method=request.method,
                        path=request.url.path,
                    )
                )
            except Exception:  # pragma: no cover - defensive
                logger.exception("try_fire_gate raised")

        response = await call_next(request)

        if request.url.path != "/health":
            body: Any = None
            if body_bytes:
                try:
                    body = json.loads(body_bytes.decode("utf-8"))
                except json.JSONDecodeError:
                    body = body_bytes.decode("utf-8", errors="ignore")

            is_sensor_request = (
                request.method == "GET"
                and _SENSOR_REQUEST_PATH_RE.match(request.url.path) is not None
            )
            event_type = "SENSOR_REQUEST" if is_sensor_request else "REST"
            message = (
                "Sensor read request"
                if is_sensor_request
                else "Incoming simulator request"
            )

            await event_store.append(
                event_type,
                source="http",
                message=message,
                endpoint=request.url.path,
                method=request.method,
                status_code=response.status_code,
                payload={
                    "query": dict(request.query_params),
                    "body": body,
                },
            )

        return response

    def _event_filter_mode(request: Request) -> str:
        """Normalize the event-filter query parameter for the current request."""
        mode = request.query_params.get("filter")
        return mode if mode in ("full", "process") else "full"

    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request) -> HTMLResponse:
        filter_mode = _event_filter_mode(request)
        return templates.TemplateResponse(
            request, "base.html", {"filter_mode": filter_mode}
        )

    # ------------------------------------------------------------------
    # HTML fragment endpoints (htmx)
    # ------------------------------------------------------------------
    @app.get("/fragments/status", response_class=HTMLResponse)
    async def fragment_status(request: Request) -> HTMLResponse:
        ctx = {"oob": False, **snapshot.all_panels()["status"]}
        return templates.TemplateResponse(request, "fragments/status.html", ctx)

    @app.get("/fragments/presets", response_class=HTMLResponse)
    async def fragment_presets(request: Request) -> HTMLResponse:
        ctx = {"oob": False, **snapshot.presets_view()}
        return templates.TemplateResponse(request, "fragments/presets.html", ctx)

    @app.get("/fragments/twin", response_class=HTMLResponse)
    async def fragment_twin(request: Request) -> HTMLResponse:
        ctx = {"oob": False, **snapshot.twin_view()}
        return templates.TemplateResponse(request, "fragments/twin.html", ctx)

    @app.get("/fragments/events", response_class=HTMLResponse)
    async def fragment_events(request: Request) -> HTMLResponse:
        mode = _event_filter_mode(request)
        ctx = {"oob": False, **snapshot.events_view(filter_mode=mode)}
        return templates.TemplateResponse(request, "fragments/events.html", ctx)

    @app.get("/fragments/pending", response_class=HTMLResponse)
    async def fragment_pending(request: Request) -> HTMLResponse:
        ctx = {"oob": False, **snapshot.pending_view()}
        return templates.TemplateResponse(request, "fragments/pending.html", ctx)

    @app.get("/fragments/sensors/{sensor_id}/preview", response_class=HTMLResponse)
    async def fragment_sensor_preview(sensor_id: str, request: Request) -> HTMLResponse:
        sensor = sensor_registry.live.get(sensor_id)
        if sensor is None:
            raise HTTPException(status_code=404, detail="sensor not found")

        clone = sensor.clone()
        params = dict(request.query_params)

        # Apply draft values to the clone without persisting
        from simulated_factory.sensors.color import ColorSensor
        from simulated_factory.sensors.distance import DistanceSensor

        if isinstance(clone, ColorSensor):
            r = int(params.get("r", 0))
            g = int(params.get("g", 0))
            b = int(params.get("b", 0))
            draft_raw = [r, g, b]
            clone.apply_update({"raw_color": draft_raw})
            # If a named color was explicitly selected, override derivation
            if params.get("value"):
                clone._cfg.value = params["value"].upper()
            template_name = "fragments/sensor_card_color.html"
        elif isinstance(clone, DistanceSensor):
            if "value" in params and params["value"] != "":
                from simulated_factory.utils import validate_distance_range
                try:
                    clone.apply_update({"value": float(params["value"])})
                except ValueError:
                    raise HTTPException(status_code=422, detail="distance out of range")
            template_name = "fragments/sensor_card_distance.html"
        else:
            raise HTTPException(status_code=400, detail="preview not supported for this sensor type")

        from fastapi.encoders import jsonable_encoder as _enc
        locked = engine.get_status().status == SimulationStatus.RUNNING
        ctx = {"sensor": _enc(clone.to_config()), "locked": locked, "preview": True}
        return templates.TemplateResponse(request, template_name, ctx)

    # ------------------------------------------------------------------
    # Server-Sent Events live stream
    # ------------------------------------------------------------------
    def _render_all_oob(request: Request) -> str:
        """Render every panel as an out-of-band swap fragment."""
        filter_mode = _event_filter_mode(request)
        panels = snapshot.all_panels(filter_mode=filter_mode)
        parts: list[str] = []
        for name in ("status", "presets", "twin", "events", "pending"):
            response = templates.TemplateResponse(
                request,
                f"fragments/{name}.html",
                {"oob": True, **panels[name]},
            )
            parts.append(response.body.decode("utf-8"))
        return "".join(parts)

    @app.get("/sse/status")
    async def sse_status(request: Request) -> StreamingResponse:
        queue = event_store.subscribe()

        def _format_sse(data: str, event: str = "update") -> bytes:
            return format_sse(data, event)

        async def event_generator():
            last_state: str = ""
            try:
                yield _format_sse(_render_all_oob(request))
                while True:
                    if await request.is_disconnected():
                        break
                    try:
                        await asyncio.wait_for(queue.get(), timeout=1.0)
                        current_state = _render_all_oob(request)
                        if current_state != last_state:
                            yield _format_sse(current_state)
                            last_state = current_state
                    except asyncio.TimeoutError:
                        yield b": ping\n\n"
            finally:
                event_store.unsubscribe(queue)

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    # ------------------------------------------------------------------
    # Simulation visibility and control
    # ------------------------------------------------------------------
    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/status")
    async def get_status() -> JSONResponse:
        return JSONResponse(snapshot.status_view())

    @app.get("/api/presets")
    async def list_presets() -> dict[str, Any]:
        presets = [
            {
                "name": preset.name,
                "description": preset.description,
                "steps": [{"name": step.name} for step in preset.steps],
            }
            for preset in sensor_registry.get_presets().values()
        ]
        return {"items": presets}

    @app.post("/api/presets/run", status_code=202)
    @app.post("/api/simulations/run", status_code=202)
    async def run_preset(request_body: RunPresetRequest) -> dict[str, str]:
        try:
            run_id = await engine.run_preset(request_body.preset, request_body.speed)
        except KeyError:
            raise HTTPException(
                status_code=404, detail=f"Unknown preset {request_body.preset}"
            )
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
        return JSONResponse(jsonable_encoder(sensor_registry.configs()))

    @app.get("/api/inventory")
    async def get_inventory() -> JSONResponse:
        return JSONResponse(inventory_poller.get_cache())

    @app.put("/api/config/sensors/{sensor_id}", response_model=None)
    async def update_sensor(
        sensor_id: str, request: Request
    ) -> JSONResponse:
        body = await request.body()
        if not body:
            payload: dict[str, Any] = {}
        else:
            try:
                payload = json.loads(body.decode("utf-8"))
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="invalid JSON body")

        # Reject writes while a preset is running
        if engine.get_status().status == SimulationStatus.RUNNING:
            raise HTTPException(
                status_code=409,
                detail="Sensor updates are locked while a preset is running",
            )

        try:
            update = SensorUpdateRequest(**payload)
        except Exception as exc:  # pydantic ValidationError
            raise HTTPException(status_code=422, detail=str(exc))

        sensor = await engine.update_sensor(sensor_id, update)

        return JSONResponse(jsonable_encoder(sensor))

    @app.get("/api/events")
    async def list_events(
        page: int = 1,
        pageSize: int = 50,
        filter: str | None = None,
        mode: str | None = None,
    ) -> dict[str, Any]:
        # Backward compat: `filter` historically accepted free-text. If it matches
        # a known mode keyword, treat it as the filter mode. The new explicit
        # `mode` param wins when both are given.
        filter_mode = mode
        text_filter: str | None = filter
        if filter in ("full", "process"):
            filter_mode = filter_mode or filter
            text_filter = None
        items, next_page = event_store.list_events(
            page=page,
            page_size=pageSize,
            filter_text=text_filter,
            filter_mode=filter_mode,
        )
        return {"items": items, "nextPage": next_page}

    @app.post("/api/events", status_code=202)
    async def accept_event(payload: Any = Body(...)) -> dict[str, str]:
        await engine.record_external_event(payload)
        return {"status": "accepted"}

    @app.post("/api/dobot/{name}/commands", status_code=202)
    async def actuator_commands(name: str, payload: Any = Body(...)) -> dict[str, Any]:
        try:
            result = await engine.handle_actuator_commands(name, payload)
        except KeyError:
            raise HTTPException(status_code=404, detail=f"Unknown robot {name}")
        return result

    @app.post("/api/gate/fire")
    async def fire_gate() -> dict[str, str]:
        fired = engine.try_fire_gate(TriggerEvent(type="manual"))
        if not fired:
            raise HTTPException(status_code=404, detail="no active manual gate")
        return {"status": "fired"}

    @app.post("/api/gate/reject")
    async def reject_gate() -> dict[str, str]:
        rejected = engine.reject_active_gate()
        if not rejected:
            raise HTTPException(status_code=404, detail="no active manual gate")
        return {"status": "rejected"}

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
        try:
            state = actuator_registry.get_state(name)
        except KeyError:
            raise HTTPException(status_code=404, detail=f"Unknown robot {name}")
        return JSONResponse(jsonable_encoder(state))

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

    return app
