# Zone Configuration System — User Guide

## Overview

The **Zone Configuration System** provides an input-friendly mechanism for creating PPE compliance zones linked to cameras. This replaces manual YAML editing with a guided CLI workflow suitable for non-technical users.

### Key Features

✅ **Camera Selection CLI** — Choose from configured cameras  
✅ **Zone Type Presets** — Pre-defined hazard levels (High/Medium/Low) with automatic PPE rules  
✅ **Automatic Configuration** — Generate valid zone configs with camera linkage  
✅ **YAML Persistence** — Seamlessly save to `config/zones.yaml`  
✅ **Backward Compatible** — Works with existing detection and rules engine  

---

## Quick Start

### 1. Interactive Zone Configuration

Run the CLI tool:

```bash
python -m src.config_manager.interactive_zones
```

**Workflow:**
1. View available cameras (e.g., "Main Entrance", "Welding Bay A")
2. Select a camera by index
3. View available zone types (High/Medium/Low Hazard)
4. Select a zone type by index
5. Review generated configuration
6. Zone is saved to `config/zones.yaml` with a unique zone ID

**Example Output:**
```
✓ Selected camera: cam-001 (Main Entrance)
✓ Selected zone type: High Hazard

============================================================
✅ Zone Configuration Created Successfully!
============================================================
Zone ID:          cam-001-high-hazard
Camera ID:        cam-001
Zone Type:        High Hazard
Required PPE:     hard_hat, vest, gloves
Alert Cooldown:   15s
============================================================
```

### 2. Programmatic Usage

Create zones from Python code:

```python
from src.config_manager.interactive_zones import interactive_configure

# Run interactive workflow
zone_id = interactive_configure()
if zone_id:
    print(f"Created zone: {zone_id}")
```

---

## Architecture

### Zone Preset System (`presets.py`)

Defines reusable zone configurations indexed by hazard level:

```python
ZONE_PRESETS = {
    "High Hazard": {
        "description": "Maximum protection required",
        "required_ppe": ["hard_hat", "vest", "gloves"],
        "alert_cooldown_seconds": 15,
    },
    "Medium Hazard": { ... },
    "Low Hazard": { ... },
}
```

**Key Exports:**
- `ZONE_PRESETS` — Master preset dictionary
- `get_zone_preset(name)` — Retrieve a preset by name
- `list_zone_types()` — Get all available zone type names

### Interactive CLI (`interactive_zones.py`)

Implements the guided zone creation workflow:

1. **`load_cameras()`** → Reads cameras from `config/cameras.yaml`
2. **`load_zones()`** → Reads existing zones from `config/zones.yaml`
3. **`select_camera(cameras)`** → User selects from displayed list
4. **`select_zone_type()`** → User selects from preset types
5. **`generate_zone_id(camera_id, zone_type)`** → Creates unique ID
6. **`create_zone_config(...)`** → Builds complete zone config
7. **`save_zones(zones, class_map)`** → Persists to YAML

**Key Exports:**
- `interactive_configure()` — Run full workflow (returns zone_id or None)
- `main()` — CLI entry point

### Zone Rules Engine Integration (`zone_rules.py`)

The `ZoneRulesEngine.evaluate()` method:

- ✓ Validates zone exists
- ✓ **NEW:** Validates zone belongs to camera (via `camera_id` field)
- ✓ Extracts required PPE from zone config
- ✓ Checks each person for missing equipment
- ✓ Respects cooldown to prevent alert flooding
- ✓ Returns list of violations

---

## Generated Zone Configuration

Each zone created via the CLI has this structure in `config/zones.yaml`:

```yaml
zones:
  cam-001-high-hazard:
    name: "High Hazard — cam-001"
    required_ppe: ["hard_hat", "vest", "gloves"]
    alert_cooldown_seconds: 15
    camera_id: "cam-001"          # Links zone to camera
```

**Key Fields:**

| Field | Type | Purpose |
|-------|------|---------|
| `name` | str | Descriptive zone name |
| `required_ppe` | list | PPE items that must be worn |
| `alert_cooldown_seconds` | int | Minimum seconds between repeated alerts |
| `camera_id` | str | **Links zone to specific camera** |

---

## Integration Points

### 1. FastAPI Application (`src/api/main.py`)

The application loads zones at startup:

```python
zones_cfg = yaml.safe_load(Path("config/zones.yaml").read_text())
rules_engine = ZoneRulesEngine(zones_cfg["zones"])
```

Changes to `zones.yaml` require **service restart** to take effect.

### 2. Stream Processor

Each camera is associated with a zone via `zone_id`:

```python
proc = StreamProcessor(
    camera_id=cam["id"],
    zone_id=cam["zone_id"],  # From cameras.yaml
    ...
)
```

For multi-zone scenarios per camera, extend cameras.yaml to allow multiple zone IDs.

### 3. Zone-Camera Validation

The rules engine now validates that a zone belongs to the camera processing it:

```python
zone_camera = zone.get("camera_id")
if zone_camera != camera_id:
    logger.debug("Zone '%s' does not belong to camera '%s' — skipping.", zone_id, camera_id)
    return []
```

This prevents cross-camera violations and ensures data integrity.

---

## Usage Examples

### Example 1: Configure Welding Bay

```bash
$ python -m src.config_manager.interactive_zones

[0] cam-002            | Welding Bay A         | ✓ ENABLED
[1] cam-003            | Chemical Storage      | ✓ ENABLED

Enter camera index: 0

[0] High Hazard        | PPE: hard_hat, vest, gloves
[1] Medium Hazard      | PPE: hard_hat, vest
[2] Low Hazard         | PPE: vest

Enter zone type index: 0

# Result: cam-002-high-hazard zone created
```

### Example 2: Programmatic Zone Creation

```python
from src.config_manager.presets import get_zone_preset
from src.config_manager.interactive_zones import (
    load_zones,
    create_zone_config,
    save_zones,
)

# Load existing zones
zones, class_map = load_zones()

# Create High Hazard zone for cam-001
preset = get_zone_preset("High Hazard")
zone_config = create_zone_config("cam-001", "High Hazard", "High Hazard", preset)

# Save
zones["cam-001-high-hazard"] = zone_config
save_zones(zones, class_map)
```

---

## Extending the System

### Add New Zone Type

Edit `src/config_manager/presets.py`:

```python
ZONE_PRESETS = {
    "Custom Zone": {
        "description": "Your custom description",
        "required_ppe": ["hard_hat", "gloves"],
        "alert_cooldown_seconds": 20,
    },
    # ... other zones
}
```

### API Endpoint for Zone Creation

To expose zone creation via REST API (future enhancement):

```python
@app.post("/zones", response_model=dict)
def create_zone_via_api(camera_id: str, zone_type: str) -> dict:
    zone_id = interactive_zones.interactive_configure()
    return {"zone_id": zone_id, "status": "created"}
```

### Web UI Integration

The interactive CLI can be wrapped in a web interface:

- **Frontend:** HTML/JS dropdown forms
- **Backend:** FastAPI endpoint calls `interactive_configure()`
- **Result:** Zone created without user touching YAML

---

## Testing

Run the integration test suite:

```bash
python test_zone_configuration.py
```

Tests verify:
- ✓ Preset definitions
- ✓ Zone ID generation
- ✓ Zone config creation
- ✓ Zone Rules Engine camera validation
- ✓ YAML persistence

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "No cameras found" | Configure cameras in `config/cameras.yaml` first |
| Zone not enforced | Restart the Inspection AI service after creating zones |
| Missing camera_id in zone | Use interactive CLI — it auto-adds this field |
| Cross-camera violations | Rules engine now validates camera_id — this shouldn't happen |

---

## Migration Guide

### From Manual YAML to CLI

**Before (Manual):**
```yaml
zones:
  zone-entry:
    name: "General Entry"
    required_ppe: ["hard_hat"]
    alert_cooldown_seconds: 30
```

**After (CLI-Generated):**
```yaml
zones:
  cam-001-low-hazard:
    name: "Low Hazard — cam-001"
    required_ppe: ["vest"]
    alert_cooldown_seconds: 60
    camera_id: "cam-001"  # NEW: Auto-linked to camera
```

---

## API Reference

### `presets.py`

```python
get_zone_preset(zone_type_name: str) -> dict | None
    # Get preset by name
    
list_zone_types() -> list[str]
    # Get all available zone type names
```

### `interactive_zones.py`

```python
interactive_configure() -> str | None
    # Run full workflow; returns zone_id or None

load_cameras() -> list[dict]
    # Load cameras from config/cameras.yaml
    
load_zones() -> tuple[dict, dict]
    # Load zones from config/zones.yaml
    # Returns (zones_dict, class_map_dict)
    
generate_zone_id(camera_id: str, zone_type: str) -> str
    # Generate zone_id from camera and type
    
create_zone_config(camera_id, zone_type, zone_type_name, preset) -> dict
    # Build zone configuration dict

save_zones(zones: dict, class_map: dict) -> None
    # Persist zones to config/zones.yaml
```

---

## Next Steps

1. **Run interactive CLI** to create first zone
2. **Restart service** to load new zones
3. **Monitor violations** via `/violations` API endpoint
4. **(Optional) Extend to REST API** for programmatic zone creation
5. **(Optional) Build web UI** for non-technical users

---

## Contact & Support

For issues or feature requests related to zone configuration, refer to the inline code documentation in:
- `src/config_manager/presets.py`
- `src/config_manager/interactive_zones.py`
- `src/detection/zone_rules.py`
