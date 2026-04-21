"""
FastAPI Application
===================
Exposes REST API and web UI for PPE Compliance System:

API Endpoints:
  GET  /                          – Root (redirects to admin panel)
  GET  /admin                     – Zone configuration web UI
  GET  /zone-presets              – Available zone types (for API/UI)
  POST /zones                     – Create new zone
  GET  /cameras                   – List configured cameras
  GET  /violations                – Paginated violation audit log
  GET  /violations/{id}           – Single violation detail
  GET  /evidence/{id}/image       – Serve violation snapshot image
  WS   /ws/alerts                 – Real-time violation alerts (WebSocket)
  GET  /stream/{camera_id}        – MJPEG live preview (for dashboard)

Static Assets:
  GET  /static/css/*              – Stylesheets
  GET  /static/js/*               – JavaScript files

This application serves both a REST API for programmatic access and a web UI
for non-technical users to configure zones, view violations, and manage the system.
"""
from __future__ import annotations

import asyncio
import json
import logging
import queue
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator, Optional

import cv2
import yaml
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware

from src.database.session import init_db, get_session
from src.database import models as db_models
from src.detection.detector import PPEDetector
from src.detection.zone_rules import ZoneRulesEngine
from src.evidence.store import EvidenceStore
from src.ingestion.stream_processor import StreamProcessor
from src.api.schemas import ViolationOut, CameraOut
from src.config_manager.interactive_zones import (
    load_zones,
    generate_zone_id,
    create_zone_config,
    save_zones,
)
from src.config_manager.presets import ZONE_PRESETS, get_zone_preset

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Shared state (populated during startup)
# ---------------------------------------------------------------------------
_result_queue: queue.Queue = queue.Queue(maxsize=256)
_processors: dict[str, StreamProcessor] = {}
_ws_clients: list[WebSocket] = []
_latest_frames: dict[str, object] = {}   # camera_id -> latest annotated ndarray


# ---------------------------------------------------------------------------
# Lifespan: start/stop stream processors
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    init_db()

    cameras_cfg = yaml.safe_load(Path("config/cameras.yaml").read_text())
    zones_cfg = yaml.safe_load(Path("config/zones.yaml").read_text())

    class_map: dict[str, str] = zones_cfg.get("class_map", {})
    model_cfg = cameras_cfg.get("model", {})
    detector = PPEDetector(
        model_path=model_cfg.get("path", "yolov8n.pt"),
        class_map=class_map,
        confidence_threshold=float(model_cfg.get("confidence", 0.45)),
        device=str(model_cfg.get("device", "cpu")),
        enable_tracking=bool(model_cfg.get("enable_tracking", True)),
    )
    rules_engine = ZoneRulesEngine(zones_cfg["zones"])
    evidence_store = EvidenceStore()

    for cam in cameras_cfg.get("cameras", []):
        if not cam.get("enabled", True):
            continue
        proc = StreamProcessor(
            camera_id=cam["id"],
            zone_id=cam["zone_id"],
            uri=str(cam["uri"]),
            detector=detector,
            rules_engine=rules_engine,
            result_queue=_result_queue,
            fps_limit=float(cam.get("fps_limit", 5)),
        )
        _processors[cam["id"]] = proc
        proc.start()
        logger.info("Started processor for camera %s", cam["id"])

    # Background task: drain result queue and broadcast violations
    async def _drain_queue() -> None:
        loop = asyncio.get_running_loop()
        while True:
            try:
                result = await loop.run_in_executor(None, _result_queue.get, True, 0.1)
            except Exception:
                await asyncio.sleep(0.05)
                continue

            # Store latest frame for MJPEG stream
            frame = result.annotated_frame if result.annotated_frame is not None else result.raw_frame
            if frame is not None:
                _latest_frames[result.camera_id] = frame

            # Persist evidence
            evidence_store.save(result)

            # Broadcast to WebSocket clients
            if result.violations and _ws_clients:
                payload = json.dumps({
                    "camera_id": result.camera_id,
                    "zone_id": result.zone_id,
                    "timestamp_utc": result.timestamp_utc,
                    "violations": [
                        {
                            "track_id": v.track_id,
                            "missing_ppe": v.missing_ppe,
                            "frame_index": v.frame_index,
                        }
                        for v in result.violations
                    ],
                })
                dead: list[WebSocket] = []
                for ws in _ws_clients:
                    try:
                        await ws.send_text(payload)
                    except Exception:
                        dead.append(ws)
                for ws in dead:
                    _ws_clients.remove(ws)

    asyncio.create_task(_drain_queue())
    yield

    for proc in _processors.values():
        proc.stop()


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(title="Inspection AI — PPE Compliance", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Template and Static Files Setup
# ---------------------------------------------------------------------------
# Configure Jinja2 template rendering for HTML pages
# Templates are loaded from src/api/templates/
api_dir = Path(__file__).parent
templates_dir = api_dir / "templates"
templates = Jinja2Templates(directory=str(templates_dir))

# Mount static files (CSS, JavaScript, images)
# Accessible at /static/{path}
static_dir = api_dir / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    logger.info("Static files mounted at /static")
else:
    logger.warning("Static directory not found at %s", static_dir)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/")
def root():
    """
    API Root Endpoint

    Returns service information and available endpoints.
    Redirects browser clients to /admin for web UI.
    """
    return {
        "service": "Inspection AI — PPE Compliance",
        "version": "0.1.0",
        "docs": "/docs",
        "admin_ui": "/admin",
        "endpoints": {
            "admin_ui": "GET /admin",
            "zone_presets": "GET /zone-presets",
            "create_zone": "POST /zones",
            "cameras": "GET /cameras",
            "violations": "GET /violations",
            "violation_detail": "GET /violations/{id}",
            "evidence_image": "GET /evidence/{id}/image",
            "live_alerts": "WS  /ws/alerts",
            "live_stream": "GET /stream/{camera_id}",
        },
    }


@app.get("/admin")
def admin_page(request: Request):
    """
    Zone Configuration Admin Page

    Serves the web UI for creating camera-specific PPE compliance zones.

    The page includes:
    - Camera selection dropdown (populated from /cameras endpoint)
    - Zone type selection dropdown (populated from /zone-presets endpoint)
    - Real-time configuration preview
    - Form submission to POST /zones endpoint

    This endpoint returns HTML rendered from the admin.html template.
    JavaScript on the page handles all API interactions.
    """
    # Jinja2Templates.TemplateResponse requires a Request object
    # to properly generate URLs with url_for()
    return templates.TemplateResponse(name="admin.html", context={"request": request}, request=request)


@app.get("/zone-presets")
def get_zone_presets() -> dict:
    """
    Get Available Zone Type Presets

    Returns all predefined zone types (High Hazard, Medium Hazard, Low Hazard)
    with their configuration details.

    Used by:
    - Web UI to populate zone type dropdown
    - API clients to display available options for zone creation

    Response format:
    {
        "High Hazard": {
            "description": "Maximum protection required...",
            "required_ppe": ["hard_hat", "vest", "gloves"],
            "alert_cooldown_seconds": 15
        },
        ...
    }

    Returns
    -------
    dict
        Mapping of zone type name → preset configuration
    """
    return ZONE_PRESETS


@app.post("/zones")
def create_zone(camera_id: str, zone_type: str) -> dict:
    """
    Create New Zone

    Creates a new PPE compliance zone linked to a specific camera.

    The zone is generated from the selected preset and saved to config/zones.yaml.
    After zone creation, the Inspection AI service must be restarted to load the new zone.

    Parameters
    ----------
    camera_id : str
        The camera this zone applies to (e.g., "cam-001")
    zone_type : str
        The zone type/preset name (e.g., "High Hazard")

    Returns
    -------
    dict
        Result containing:
        - zone_id: Generated zone identifier
        - status: "created"
        - message: Confirmation message

    Raises
    ------
    HTTPException 400
        If camera_id or zone_type is invalid
    HTTPException 500
        If zone creation fails (file I/O error, etc.)

    Example
    -------
    POST /zones?camera_id=cam-001&zone_type=High%20Hazard

    Response:
    {
        "zone_id": "cam-001-high-hazard",
        "status": "created",
        "message": "Zone created successfully"
    }
    """
    try:
        # Validate camera exists
        cameras_cfg = yaml.safe_load(Path("config/cameras.yaml").read_text())
        camera_ids = [c["id"] for c in cameras_cfg.get("cameras", [])]
        if camera_id not in camera_ids:
            raise HTTPException(
                status_code=400,
                detail=f"Camera '{camera_id}' not found. Available: {camera_ids}"
            )

        # Validate zone type exists
        preset = get_zone_preset(zone_type)
        if preset is None:
            raise HTTPException(
                status_code=400,
                detail=f"Zone type '{zone_type}' not found. Available: {list(ZONE_PRESETS.keys())}"
            )

        # Generate zone configuration
        zone_id = generate_zone_id(camera_id, zone_type)
        zone_config = create_zone_config(camera_id, zone_type, zone_type, preset)

        # Load existing zones and update
        zones, class_map = load_zones()
        zones[zone_id] = zone_config

        # Save updated zones
        save_zones(zones, class_map)

        logger.info(
            "Zone created via API: %s (camera=%s, type=%s)",
            zone_id,
            camera_id,
            zone_type,
        )

        return {
            "zone_id": zone_id,
            "status": "created",
            "message": f"Zone '{zone_id}' created successfully. Restart service to apply.",
        }

    except yaml.YAMLError as e:
        logger.error("YAML error during zone creation: %s", e)
        raise HTTPException(status_code=500, detail=f"Configuration error: {e}")
    except FileNotFoundError as e:
        logger.error("Configuration file not found: %s", e)
        raise HTTPException(status_code=500, detail=f"Configuration file error: {e}")
    except Exception as e:
        logger.error("Unexpected error during zone creation: %s", e)
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")


@app.get("/cameras", response_model=list[CameraOut])
def list_cameras() -> list[CameraOut]:
    cfg = yaml.safe_load(Path("config/cameras.yaml").read_text())
    return [
        CameraOut(
            id=c["id"],
            name=c["name"],
            zone_id=c["zone_id"],
            enabled=c.get("enabled", True),
            running=c["id"] in _processors,
        )
        for c in cfg.get("cameras", [])
    ]


@app.get("/violations", response_model=list[ViolationOut])
def list_violations(
    camera_id: Optional[str] = None,
    zone_id: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> list[ViolationOut]:
    with get_session() as session:
        q = session.query(db_models.ViolationRecord)
        if camera_id:
            q = q.filter(db_models.ViolationRecord.camera_id == camera_id)
        if zone_id:
            q = q.filter(db_models.ViolationRecord.zone_id == zone_id)
        records = q.order_by(db_models.ViolationRecord.id.desc()).offset(offset).limit(limit).all()
        return [ViolationOut.model_validate(r) for r in records]


@app.get("/violations/{violation_id}", response_model=ViolationOut)
def get_violation(violation_id: int) -> ViolationOut:
    with get_session() as session:
        record = session.get(db_models.ViolationRecord, violation_id)
        if not record:
            raise HTTPException(status_code=404, detail="Not found")
        return ViolationOut.model_validate(record)


@app.get("/evidence/{violation_id}/image")
def get_evidence_image(violation_id: int) -> FileResponse:
    with get_session() as session:
        record = session.get(db_models.ViolationRecord, violation_id)
        if not record or not record.snapshot_path:
            raise HTTPException(status_code=404, detail="Evidence image not found")
        path = Path(record.snapshot_path)
        if not path.exists():
            raise HTTPException(status_code=404, detail="File not found on disk")
        return FileResponse(path, media_type="image/jpeg")


@app.websocket("/ws/alerts")
async def ws_alerts(websocket: WebSocket) -> None:
    await websocket.accept()
    _ws_clients.append(websocket)
    try:
        while True:
            # Keep connection alive; actual data is pushed from the drain task
            await websocket.receive_text()
    except WebSocketDisconnect:
        _ws_clients.remove(websocket)


@app.get("/stream/{camera_id}")
async def mjpeg_stream(camera_id: str) -> StreamingResponse:
    """MJPEG live preview — serves the latest annotated frame per camera."""
    if camera_id not in _processors:
        raise HTTPException(status_code=404, detail="Camera not running")

    async def _generate():
        while True:
            frame = _latest_frames.get(camera_id)
            if frame is not None:
                _, jpeg = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                yield (
                    b"--frame\r\nContent-Type: image/jpeg\r\n\r\n"
                    + jpeg.tobytes()
                    + b"\r\n"
                )
            await asyncio.sleep(0.04)   # ~25 fps max

    return StreamingResponse(
        _generate(),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )
