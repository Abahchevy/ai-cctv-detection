# Inspection AI — PPE Compliance System
## Technical Documentation

**Project:** AI-Enabled CCTV System for PPE Compliance  
**Purpose:** Real-time, context-aware monitoring of Personal Protective Equipment (PPE) across high-risk operational areas  
**Date:** April 2026  
**Stack:** Python 3.x · YOLOv8 · FastAPI · OpenCV · SQLite · SQLAlchemy

---

## 1. System Overview

The system provides automated, real-time PPE compliance monitoring by:

1. Ingesting live video feeds from CCTV cameras (RTSP or local webcam)
2. Running AI inference to detect persons and their PPE usage
3. Evaluating detections against zone-specific PPE requirements
4. Generating auditable evidence (annotated JPEG snapshots + database records)
5. Exposing a REST API, WebSocket alert stream, and MJPEG live view

### Architecture Diagram

```
CCTV Cameras (RTSP / Webcam)
          │
          ▼
┌─────────────────────┐
│   StreamProcessor    │  One daemon thread per camera
│   (src/ingestion/)   │  Reads frames at configured FPS limit
│                      │  Auto-reconnects on stream failure
└──────────┬──────────┘
           │ BGR frames
           ▼
┌─────────────────────┐
│    PPEDetector       │  YOLOv8 model inference (ultralytics)
│   (src/detection/)   │  Detects persons + PPE items per frame
│                      │  Groups PPE detections to nearest person
└──────────┬──────────┘
           │ PersonObservation list
           ▼
┌─────────────────────┐
│  ZoneRulesEngine     │  Compares worn PPE vs zone requirements
│   (src/detection/)   │  Per-person cooldown suppresses repeat alerts
│                      │  Produces Violation records
└──────────┬──────────┘
           │ Violations
           ▼
┌─────────────────────┐     ┌───────────────────────┐
│   EvidenceStore      │────▶│  SQLite Database       │
│   (src/evidence/)    │     │  inspection_ai.db      │
│                      │     │  (violations table)    │
│   + Frame Annotator  │────▶│  JPEG Snapshots        │
│                      │     │  evidence/<cam>/<date>/ │
└──────────┬──────────┘     └───────────────────────┘
           │
           ▼
┌─────────────────────┐
│   FastAPI Backend    │  REST API + WebSocket alerts + MJPEG preview
│    (src/api/)        │  http://localhost:8000
└─────────────────────┘
```

---

## 2. Project File Structure

```
inspection-ai/
│
├── run.py                          Entry point — starts the FastAPI/uvicorn server
├── requirements.txt                Python dependencies
│
├── config/
│   ├── cameras.yaml                Camera definitions, model config, FPS limits
│   └── zones.yaml                  Zone PPE requirements + model class name mapping
│
├── models/
│   └── best.pt                     YOLOv8m hard-hat detection model (49.6 MB)
│                                   Source: keremberke/yolov8m-hard-hat-detection (HuggingFace)
│
├── src/
│   ├── api/
│   │   ├── main.py                 FastAPI app, lifespan startup, all HTTP/WS routes
│   │   └── schemas.py              Pydantic response models (CameraOut, ViolationOut)
│   │
│   ├── database/
│   │   ├── models.py               SQLAlchemy ORM model — ViolationRecord table
│   │   └── session.py              SQLite engine, session factory, init_db()
│   │
│   ├── detection/
│   │   ├── detector.py             PPEDetector class — wraps YOLO, groups PPE to persons
│   │   ├── models.py               Dataclasses: BoundingBox, Detection, PersonObservation,
│   │   │                           FrameResult, Violation
│   │   └── zone_rules.py           ZoneRulesEngine — evaluates violations + cooldown cache
│   │
│   ├── evidence/
│   │   ├── annotator.py            OpenCV frame annotator — draws boxes, labels, timestamps
│   │   └── store.py                EvidenceStore — saves JPEG + writes DB record per violation
│   │
│   └── ingestion/
│       └── stream_processor.py     StreamProcessor thread — reads RTSP/webcam, calls pipeline
│
├── evidence/                       Auto-created — stores annotated violation snapshots
│   └── <camera_id>/
│       └── <YYYY-MM-DD>/
│           └── <HHMMSS>_frame<N>.jpg
│
└── inspection_ai.db                Auto-created SQLite database
```

---

## 3. Configuration Reference

### `config/cameras.yaml`

```yaml
model:
  path: "models/best.pt"    # Path to YOLOv8 .pt weights file
  confidence: 0.40          # Detection confidence threshold (0–1)
  device: "cpu"             # "cpu" or "cuda" (NVIDIA GPU)
  enable_tracking: false    # ByteTrack person tracking (requires 'lap' package)

cameras:
  - id: cam-test                    # Unique camera identifier
    name: "Local Test Feed (Webcam)"
    uri: "0"                        # "0" = webcam, or "rtsp://..." for IP cameras
    zone_id: zone-entry             # Must match a key in zones.yaml
    fps_limit: 10                   # Max frames/sec to process
    enabled: true                   # Set false to skip this camera
```

**RTSP camera example:**
```yaml
- id: cam-gate
  name: "Site Gate"
  uri: "rtsp://admin:password@192.168.1.100:554/stream1"
  zone_id: zone-entry
  fps_limit: 5
  enabled: true
```

### `config/zones.yaml`

Defines which PPE items are mandatory per operational area, and maps the model's raw class names to canonical PPE identifiers.

```yaml
zones:
  zone-entry:
    name: "General Entry / Site Boundary"
    required_ppe:
      - hard_hat              # Any person without this triggers a violation
    alert_cooldown_seconds: 30

class_map:
  "helmet": hard_hat          # Model class name -> canonical PPE id
  "person": person
```

**How class mapping works:**
- The YOLO model outputs raw class labels (e.g. `"helmet"`, `"head"`, `"person"`)
- `class_map` translates those to canonical ids used in zone rules
- Classes not in `class_map` are ignored (e.g. `"head"` = bare head = no PPE detected)

---

## 4. AI Model

| Property | Value |
|---|---|
| Model | `keremberke/yolov8m-hard-hat-detection` |
| Architecture | YOLOv8m (medium) |
| File | `models/best.pt` (49.6 MB) |
| Input | BGR image frame |
| Output classes | `helmet`, `head`, `person` |
| Inference backend | Ultralytics (CPU or CUDA) |

**Detection logic:**
- `person` → bounding box for a detected human
- `helmet` → hard hat detected near a person → **compliant** (green box)
- `head` or no helmet class near person → **violation** (red box, alert generated)

**PPE-to-person attribution:**
Each PPE detection centre is checked against all person bounding boxes. A PPE item is attributed to a person if its centre falls within 1.2× the person's bounding box dimensions. This handles overlapping detections robustly.

---

## 5. API Endpoints

Base URL: `http://localhost:8000`

### REST Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | Service info and endpoint index |
| `GET` | `/cameras` | List all configured cameras and running status |
| `GET` | `/violations` | Paginated audit log of all violations |
| `GET` | `/violations/{id}` | Single violation record |
| `GET` | `/evidence/{id}/image` | Serve annotated JPEG snapshot for a violation |
| `GET` | `/stream/{camera_id}` | MJPEG live annotated video stream |

### WebSocket

| Path | Description |
|---|---|
| `WS /ws/alerts` | Real-time violation push — JSON message per violation event |

**WebSocket message format:**
```json
{
  "camera_id": "cam-test",
  "zone_id": "zone-entry",
  "timestamp_utc": "2026-04-13T10:24:55.123456+00:00",
  "violations": [
    {
      "track_id": null,
      "missing_ppe": ["hard_hat"],
      "frame_index": 142
    }
  ]
}
```

### Query Parameters — `/violations`

| Parameter | Type | Description |
|---|---|---|
| `camera_id` | string | Filter by camera |
| `zone_id` | string | Filter by zone |
| `limit` | int (default 50) | Max records to return |
| `offset` | int (default 0) | Pagination offset |

**Interactive API docs:** `http://localhost:8000/docs`

---

## 6. Evidence Storage

Every violation generates:

**1. Annotated JPEG snapshot**
```
evidence/
  cam-test/
    2026-04-13/
      092455_frame142.jpg    # UTC time + frame number
```

The image contains:
- Coloured bounding boxes (green = compliant, red = violation)
- Person track ID label (if tracking enabled)
- "MISSING: HARD_HAT" label above violating persons
- UTC timestamp watermark

**2. SQLite database record**

Table: `violations`

| Column | Type | Description |
|---|---|---|
| id | INTEGER PK | Auto-increment |
| camera_id | TEXT | Camera source |
| zone_id | TEXT | Operational zone |
| track_id | INTEGER / NULL | Person track ID (if tracking on) |
| missing_ppe | TEXT | JSON array of missing PPE ids |
| snapshot_path | TEXT | Absolute path to JPEG |
| timestamp_utc | TEXT | ISO-8601 timestamp |
| frame_index | INTEGER | Frame number in stream |

---

## 7. Alert Cooldown

To prevent alert flooding when a person remains non-compliant, the `ZoneRulesEngine` applies a per-person cooldown:

- After a violation is raised for a person in a zone, no further alerts are generated for that `(zone_id, track_id)` pair until the cooldown window expires
- Default: **30 seconds** for entry zones, **15 seconds** for hazardous zones
- Configurable per zone in `zones.yaml` via `alert_cooldown_seconds`

> **Note:** Without tracking (`enable_tracking: false`), `track_id` is `None`, so the cooldown applies to the zone as a whole rather than per-individual. Enable tracking (requires `lap` package) for per-person precision.

---

## 8. Running the System

### Prerequisites

```
Python 3.9+
Miniconda / pip environment
ultralytics >= 8.2.0
opencv-python-headless >= 4.9.0
fastapi >= 0.111.0
uvicorn >= 0.29.0
pydantic >= 2.3.0
sqlalchemy >= 2.0.0
pyyaml >= 6.0
```

All are pre-installed in the current environment.

### Start the Server

```powershell
cd C:\Users\cquk\inspection-ai
python run.py
```

Or with auto-reload for development:
```powershell
uvicorn run:app --reload --host 0.0.0.0 --port 8000
```

### Quick Test URLs

```
http://localhost:8000/             → API index
http://localhost:8000/docs         → Interactive Swagger UI
http://localhost:8000/stream/cam-test  → Live webcam MJPEG stream
http://localhost:8000/cameras      → Camera status JSON
http://localhost:8000/violations   → Violation audit log JSON
```

---

## 9. Adding a Real RTSP Camera

1. Edit `config/cameras.yaml`
2. Add an entry under `cameras:`:

```yaml
- id: cam-site-gate
  name: "Site Gate Camera"
  uri: "rtsp://admin:your_password@192.168.1.101:554/stream1"
  zone_id: zone-entry
  fps_limit: 5
  enabled: true
```

3. Restart the server — the new camera starts automatically.

> **Security note:** Store RTSP credentials in an environment variable rather than plain text in production. Replace the URI value with `${CAMERA_GATE_URI}` and load via `python-dotenv`.

---

## 10. Swapping the AI Model

To use a different or more comprehensive PPE model (e.g. detecting vests, gloves, boots):

1. Place the `.pt` file in `models/`
2. Update `config/cameras.yaml`:
   ```yaml
   model:
     path: "models/your-new-model.pt"
   ```
3. Update `config/zones.yaml` — add required PPE ids and class_map entries to match the new model's class names
4. Update zone `required_ppe` lists accordingly
5. Restart the server

---

## 11. Known Limitations & Future Work

| Item | Current State | Recommendation |
|---|---|---|
| Person tracking | Disabled (needs `lap`) | Install `lap` via internal mirror or wheels |
| GPU acceleration | CPU only | Set `device: cuda` when NVIDIA GPU available |
| PPE scope | Hard hat only | Replace model with multi-PPE model |
| Alert delivery | WebSocket only | Add email/SMS/Teams webhook integration |
| Dashboard UI | Browser MJPEG + JSON | Build a React/Vue dashboard |
| Authentication | None | Add OAuth2/API key before production |
| RTSP credential security | Plain text YAML | Move to environment variables / secrets manager |

---

## 12. Issues Resolved During Setup

| Issue | Cause | Fix Applied |
|---|---|---|
| `TypeError: unsupported operand type(s) for \|` | Python 3.9 doesn't support `X \| None` syntax | Replaced with `Optional[X]` + `from __future__ import annotations` |
| MJPEG stream blank in browser | Shared result queue consumed by drain task before stream endpoint | Replaced with `_latest_frames` dict updated by drain task |
| Webcam returns black frames | Windows MSMF backend bug | Switched to `cv2.CAP_DSHOW` (DirectShow) for webcam indices on Windows |
| `lap` module not found | `lap` unavailable via corporate Artifactory proxy | Disabled ByteTrack (`enable_tracking: false`) |
| Hard hat model SSL error | Corporate proxy with self-signed cert blocks HuggingFace | Downloaded `best.pt` via `Net.WebClient` with cert check bypassed |
| `FileNotFoundError: keremberke/...` | Newer ultralytics treats HF repo IDs as local paths | Download `.pt` locally + reference by file path |
