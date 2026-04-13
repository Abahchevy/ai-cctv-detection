"""
FastAPI Application
===================
Exposes:
  GET  /cameras              – list configured cameras
  GET  /violations           – paginated audit log
  GET  /violations/{id}      – single record
  GET  /evidence/{id}/image  – serve snapshot JPEG
  WS   /ws/alerts            – real-time violation push over WebSocket
  GET  /stream/{camera_id}   – MJPEG live preview (for dashboard)
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
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

from src.database.session import init_db, get_session
from src.database import models as db_models
from src.detection.detector import PPEDetector
from src.detection.zone_rules import ZoneRulesEngine
from src.evidence.store import EvidenceStore
from src.ingestion.stream_processor import StreamProcessor
from src.api.schemas import ViolationOut, CameraOut

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
# Routes
# ---------------------------------------------------------------------------

@app.get("/")
def root():
    return {
        "service": "Inspection AI — PPE Compliance",
        "version": "0.1.0",
        "docs": "/docs",
        "endpoints": {
            "cameras": "GET /cameras",
            "violations": "GET /violations",
            "violation_detail": "GET /violations/{id}",
            "evidence_image": "GET /evidence/{id}/image",
            "live_alerts": "WS  /ws/alerts",
            "live_stream": "GET /stream/{camera_id}",
        },
    }

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
