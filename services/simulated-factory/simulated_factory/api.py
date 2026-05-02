from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import Body, FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.encoders import jsonable_encoder
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.templating import Jinja2Templates

from simulated_factory.adapters.distance_publisher import DistancePublisher
from simulated_factory.adapters.kafka_observer import KafkaObserver
from simulated_factory.engine import SimulationEngine
from simulated_factory.events import EventBridge, EventStore
from simulated_factory.deps import build_dependencies
from simulated_factory.models import (
    InteractiveConfig,
    InteractiveConfigRequest,
    ResolveActionRequest,
    RunPresetRequest,
    SensorUpdateRequest,
    utc_now,
)

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
    event_bridge = deps["event_bridge"]
    distance_publisher = deps["distance_publisher"]
    engine = deps["engine"]
    kafka_observer = deps["kafka_observer"]

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        await kafka_observer.start()
        engine.start_inventory_poller()
        try:
            yield
        finally:
            await engine.stop_inventory_poller()
            await kafka_observer.stop()

    app = FastAPI(
        title="Simulated Factory Service",
        version="1.0.0",
        lifespan=lifespan,
    )
    app.state.engine = engine
    app.state.event_store = event_store
    app.state.kafka_observer = kafka_observer

    @app.middleware("http")
    async def capture_requests(request: Request, call_next):
        body_bytes = await request.body()

        if request.url.path != "/health":
            # Fire any active preset gate that matches this incoming request
            # BEFORE the handler runs so its sensor reads observe the updated
            # state. Side-effects (sensor updates, distance publish) are
            # applied inside fire_gate_if_matches.
            try:
                engine.fire_gate_if_matches(request.method, request.url.path)
            except Exception:  # pragma: no cover - defensive
                logger.exception("fire_gate_if_matches raised")

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

    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request) -> HTMLResponse:
        return templates.TemplateResponse(request, "base.html", {})

    # ------------------------------------------------------------------
    # HTML fragment endpoints (htmx)
    # ------------------------------------------------------------------
    def _events_for_view(
        limit: int = 30, filter_mode: str | None = None
    ) -> list[dict[str, Any]]:
        items, _ = event_store.list_events(
            page=1, page_size=limit, filter_mode=filter_mode
        )
        return items

    def _render_fragment(
        request: Request, name: str, *, oob: bool = False, **extra: Any
    ) -> HTMLResponse:
        ctx = {"oob": oob, **extra}
        return templates.TemplateResponse(request, f"fragments/{name}.html", ctx)

    @app.get("/fragments/status", response_class=HTMLResponse)
    async def fragment_status(request: Request) -> HTMLResponse:
        return _render_fragment(
            request, "status", state=jsonable_encoder(engine.get_status())
        )

    @app.get("/fragments/presets", response_class=HTMLResponse)
    async def fragment_presets(request: Request) -> HTMLResponse:
        return _render_fragment(
            request,
            "presets",
            presets=engine.list_presets(),
            state=jsonable_encoder(engine.get_status()),
        )

    @app.get("/fragments/twin", response_class=HTMLResponse)
    async def fragment_twin(request: Request) -> HTMLResponse:
        return _render_fragment(
            request,
            "twin",
            state=jsonable_encoder(engine.get_status()),
            sensors=jsonable_encoder(engine.get_sensor_configs()),
            inventory=engine.get_inventory_cache(),
        )

    @app.get("/fragments/events", response_class=HTMLResponse)
    async def fragment_events(
        request: Request, filter: str | None = None
    ) -> HTMLResponse:
        mode = filter if filter in ("full", "process") else "full"
        return _render_fragment(
            request,
            "events",
            events=_events_for_view(filter_mode=mode),
            filter_mode=mode,
        )

    @app.get("/fragments/pending", response_class=HTMLResponse)
    async def fragment_pending(request: Request) -> HTMLResponse:
        return _render_fragment(
            request, "pending", pending=engine.get_pending_actions()
        )

    # ------------------------------------------------------------------
    # Server-Sent Events live stream
    # ------------------------------------------------------------------
    def _render_all_oob(request: Request) -> str:
        """Render every panel as an out-of-band swap fragment."""
        filter_mode = request.query_params.get("filter")
        if filter_mode not in ("full", "process"):
            filter_mode = "full"
        parts: list[str] = []
        renderers = [
            ("status", {"state": jsonable_encoder(engine.get_status())}),
            (
                "presets",
                {
                    "presets": engine.list_presets(),
                    "state": jsonable_encoder(engine.get_status()),
                },
            ),
            (
                "twin",
                {
                    "state": jsonable_encoder(engine.get_status()),
                    "sensors": jsonable_encoder(engine.get_sensor_configs()),
                    "inventory": engine.get_inventory_cache(),
                },
            ),
            (
                "events",
                {
                    "events": _events_for_view(filter_mode=filter_mode),
                    "filter_mode": filter_mode,
                },
            ),
            ("pending", {"pending": engine.get_pending_actions()}),
        ]
        for name, ctx in renderers:
            response = templates.TemplateResponse(
                request,
                f"fragments/{name}.html",
                {"oob": True, **ctx},
            )
            parts.append(response.body.decode("utf-8"))
        return "".join(parts)

    @app.get("/sse/status")
    async def sse_status(request: Request) -> StreamingResponse:
        queue = event_store.subscribe()

        def _format_sse(data: str, event: str = "update") -> bytes:
            return format_sse(data, event)

        async def event_generator():
            try:
                yield _format_sse(_render_all_oob(request))
                while True:
                    if await request.is_disconnected():
                        break
                    try:
                        await asyncio.wait_for(queue.get(), timeout=1.0)
                    except asyncio.TimeoutError:
                        yield b": ping\n\n"
                        continue
                    yield _format_sse(_render_all_oob(request))
            finally:
                event_store.unsubscribe(queue)

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

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
        return JSONResponse(jsonable_encoder(engine.get_sensor_configs()))

    @app.get("/api/inventory")
    async def get_inventory() -> JSONResponse:
        return JSONResponse(engine.get_inventory_cache())

    @app.put("/api/config/sensors/{sensor_id}", response_model=None)
    async def update_sensor(
        sensor_id: str, request: Request
    ) -> JSONResponse | HTMLResponse:
        body = await request.body()
        if not body:
            payload: dict[str, Any] = {}
        else:
            try:
                payload = json.loads(body.decode("utf-8"))
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="invalid JSON body")

        # Coerce values that may arrive as strings via htmx forms (json-enc).
        def parse_number_or_string(val: Any):
            if isinstance(val, (int, float)):
                return val
            if not isinstance(val, str):
                return val
            s = val.strip()
            if s == "":
                return None
            try:
                if "." in s:
                    return float(s)
                return int(s)
            except ValueError:
                try:
                    return float(s)
                except ValueError:
                    return s

        # raw_color: accept CSV string or list of values and coerce to ints when possible
        raw = payload.get("raw_color")
        if isinstance(raw, str):
            tokens = [t.strip() for t in raw.split(",") if t.strip()]
            coerced: list[Any] = []
            for t in tokens:
                try:
                    coerced.append(int(t))
                except Exception:
                    try:
                        coerced.append(int(float(t)))
                    except Exception:
                        coerced.append(t)
            payload["raw_color"] = coerced if coerced else None
        elif isinstance(raw, list):
            coerced = []
            for t in raw:
                if t is None or (isinstance(t, str) and t.strip() == ""):
                    continue
                if isinstance(t, (int, float)):
                    coerced.append(int(t))
                else:
                    try:
                        coerced.append(int(str(t).strip()))
                    except Exception:
                        try:
                            coerced.append(int(float(str(t).strip())))
                        except Exception:
                            coerced.append(str(t).strip())
            payload["raw_color"] = coerced if coerced else None

        # scripted_values: accept CSV string or list and coerce items to numbers when possible
        sv = payload.get("scripted_values")
        if isinstance(sv, str):
            tokens = [t.strip() for t in sv.split(",") if t.strip()]
            payload["scripted_values"] = [parse_number_or_string(t) for t in tokens]
        elif isinstance(sv, list):
            coerced_sv: list[Any] = []
            for it in sv:
                if it is None or (isinstance(it, str) and it.strip() == ""):
                    continue
                parsed = parse_number_or_string(it)
                if parsed is not None:
                    coerced_sv.append(parsed)
            payload["scripted_values"] = coerced_sv

        if "value" in payload and isinstance(payload["value"], str):
            value_str = payload["value"].strip()
            lowered = value_str.lower()
            if lowered == "true":
                payload["value"] = True
            elif lowered == "false":
                payload["value"] = False
            elif value_str == "":
                payload["value"] = None
            else:
                try:
                    if "." in value_str:
                        payload["value"] = float(value_str)
                    else:
                        payload["value"] = int(value_str)
                except ValueError:
                    payload["value"] = value_str

        try:
            update = SensorUpdateRequest(**payload)
        except Exception as exc:  # pydantic ValidationError
            raise HTTPException(status_code=422, detail=str(exc))

        sensor = await engine.update_sensor(sensor_id, update)

        if request.headers.get("HX-Request") == "true":
            # The twin panel is refreshed via the SSE OOB stream after the
            # STATE event published by update_sensor; the form itself uses
            # hx-swap="none" so we only need a minimal response body here.
            return HTMLResponse("", status_code=200)
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
    async def dobot_commands(name: str, payload: Any = Body(...)) -> dict[str, Any]:
        result = await engine.handle_dobot_commands(name, payload)
        return result

    @app.get("/api/interactive/config")
    async def get_interactive_config() -> dict[str, Any]:
        config = engine.get_interactive_config()
        return {
            "intercepted": sorted(config.intercepted),
            "timeoutSeconds": config.timeout_seconds,
        }

    @app.put("/api/interactive/config")
    async def put_interactive_config(
        request_body: InteractiveConfigRequest,
    ) -> dict[str, Any]:
        new_config = InteractiveConfig(
            intercepted=set(request_body.intercepted),
            timeout_seconds=request_body.timeoutSeconds,
        )
        config = engine.set_interactive_config(new_config)
        return {
            "intercepted": sorted(config.intercepted),
            "timeoutSeconds": config.timeout_seconds,
        }

    @app.get("/api/interactive/pending")
    async def list_pending_actions() -> dict[str, Any]:
        return {"items": engine.get_pending_actions()}

    @app.post("/api/interactive/{action_id}/resolve")
    async def resolve_pending_action(
        action_id: str, request_body: ResolveActionRequest
    ) -> dict[str, Any]:
        try:
            action = await engine.resolve_action(
                action_id, request_body.outcome, request_body.reason
            )
        except KeyError:
            raise HTTPException(
                status_code=404, detail=f"Unknown action {action_id}"
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        return {
            "actionId": action.id,
            "outcome": action.outcome,
            "reason": action.reason,
        }

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
                "pending": engine.get_pending_actions(),
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
                        "pending": engine.get_pending_actions(),
                    }
                )
        except WebSocketDisconnect:
            return
        finally:
            event_store.unsubscribe(queue)

    return app
