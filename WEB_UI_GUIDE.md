# Web UI for Zone Configuration — User & Developer Guide

## Overview

The **Zone Configuration Web UI** provides a browser-based interface for creating PPE compliance zones without touching YAML files or the command line. 

Built with:
- **Backend:** FastAPI for REST API and template serving
- **Frontend:** HTML5 + CSS3 + Vanilla JavaScript (no heavy frameworks)
- **Architecture:** API-driven with real-time form updates and preview

### Key Features

✅ **Camera Selection** — Dropdown populated from `GET /cameras`  
✅ **Zone Type Presets** — Dropdown with High/Medium/Low Hazard options  
✅ **Live Configuration Preview** — Shows exactly what will be created  
✅ **One-Click Zone Creation** — Submit form to `POST /zones`  
✅ **Real-Time Validation** — Instant feedback and error messages  
✅ **Responsive Design** — Works on desktop and mobile  
✅ **Minimal Dependencies** — No jQuery, React, or build tools required  

---

## Quick Start

### Access the Web UI

1. **Start the Inspection AI service:**
   ```bash
   python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000
   ```

2. **Open in browser:**
   ```
   http://localhost:8000/admin
   ```

3. **Create a zone:**
   - Select a camera from dropdown
   - Select zone type (High/Medium/Low Hazard)
   - Review preview
   - Click "Create Zone"
   - See confirmation message
   - **Restart service to apply changes**

### API Access (Programmatic)

```bash
# Get zone presets
curl http://localhost:8000/zone-presets

# Get cameras
curl http://localhost:8000/cameras

# Create zone
curl -X POST "http://localhost:8000/zones?camera_id=cam-001&zone_type=High%20Hazard"
```

---

## Architecture

### File Structure

```
src/api/
├── main.py                      # FastAPI app + endpoints (updated)
├── static/
│   └── css/
│       └── style.css            # Styling (minimal, no framework)
├── templates/
│   ├── base.html                # Base template with utilities
│   └── admin.html               # Zone configuration form page
└── schemas.py                   # Pydantic models (existing)
```

### Request Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    Web Browser                              │
│  [User opens http://localhost:8000/admin]                   │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│     GET /admin (FastAPI endpoint - returns admin.html)      │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│            HTML Rendered (admin.html template)              │
│  - Loads CSS from /static/css/style.css                      │
│  - Runs JavaScript to populate dropdowns                     │
└────────────────────────┬────────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
        ▼                ▼                ▼
   GET /cameras   GET /zone-presets   POST /zones
      (list)          (presets)        (create)
        │                │                │
        └────────────────┼────────────────┘
                         │
                         ▼
        ┌────────────────────────────────┐
        │   Backend (FastAPI endpoints)  │
        │  - Validates input             │
        │  - Creates zone config         │
        │  - Updates config/zones.yaml   │
        │  - Returns JSON response       │
        └────────────────────────────────┘
                         │
                         ▼
        ┌────────────────────────────────┐
        │    Browser displays result     │
        │  - Success/error alert         │
        │  - Zone ID shown               │
        │  - Form reset for next zone    │
        └────────────────────────────────┘
```

---

## REST API Endpoints

### GET /admin
**Purpose:** Serve the zone configuration web UI

**Response:** HTML page with form and JavaScript

```
GET /admin
```

**Example Usage:**
```bash
# Open in browser or fetch
curl http://localhost:8000/admin > admin_page.html
```

---

### GET /zone-presets
**Purpose:** Get available zone type presets

**Response:** JSON object mapping zone type names to configurations

```json
{
  "High Hazard": {
    "description": "Maximum protection required (e.g., chemical handling, welding)",
    "required_ppe": ["hard_hat", "vest", "gloves"],
    "alert_cooldown_seconds": 15
  },
  "Medium Hazard": { ... },
  "Low Hazard": { ... }
}
```

**Example Usage:**
```bash
curl http://localhost:8000/zone-presets | jq
```

---

### POST /zones
**Purpose:** Create a new PPE compliance zone

**Parameters:**
- `camera_id` (query, required): Camera ID (e.g., "cam-001")
- `zone_type` (query, required): Zone type name (e.g., "High Hazard")

**Response:** JSON with zone creation result

```json
{
  "zone_id": "cam-001-high-hazard",
  "status": "created",
  "message": "Zone 'cam-001-high-hazard' created successfully. Restart service to apply."
}
```

**Error Responses:**
```json
// Invalid camera_id
{ "detail": "Camera 'cam-999' not found. Available: ['cam-001', 'cam-002']" }

// Invalid zone_type
{ "detail": "Zone type 'Invalid' not found. Available: ['High Hazard', 'Medium Hazard', 'Low Hazard']" }

// File I/O error
{ "detail": "Configuration file error: ..." }
```

**Example Usage:**
```bash
# Create High Hazard zone for cam-001
curl -X POST "http://localhost:8000/zones?camera_id=cam-001&zone_type=High%20Hazard"

# With JSON request body (alternative)
curl -X POST "http://localhost:8000/zones" \
  -H "Content-Type: application/json" \
  -d '{"camera_id": "cam-001", "zone_type": "High Hazard"}'
```

---

## User Interface Guide

### Page Layout

```
┌─────────────────────────────────────────┐
│    🔧 Zone Configuration               │
│    Create PPE compliance zones...       │
└─────────────────────────────────────────┘

[Alert Zone - Success/Error Messages]

┌─────────────────────────────────────────┐
│  Zone Type *                             │
│  [Dropdown: Select zone type...]        │
│  ✓ Help text                             │
│                                          │
│  Zone Type Description:                  │
│  ✓ hard_hat                              │
│  ✓ vest                                  │
│  ✓ gloves                                │
│  Alert Cooldown: 15s                     │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│  Camera *                                │
│  [Dropdown: Select camera...]           │
│  ✓ Help text                             │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│  📋 Configuration Preview                │
│  Zone ID:          cam-001-high-hazard  │
│  Camera:           cam-001 (Main...)     │
│  Zone Type:        High Hazard           │
│  Required PPE:     hard_hat, vest...     │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│  [✨ Create Zone] [Clear]               │
└─────────────────────────────────────────┘
```

### Workflow

**Step 1: Select Zone Type**
- Opens description showing PPE requirements
- Displays alert cooldown time
- Preview updates

**Step 2: Select Camera**
- Shows which camera this zone applies to
- Preview updates with camera details

**Step 3: Review Preview**
- Zone ID automatically generated
- Shows all configuration details
- Final chance to verify before creating

**Step 4: Submit**
- Click "Create Zone" button
- Form disables during submission
- Loading spinner displayed
- Result shown in alert box

**Step 5: Complete**
- Success/error message displayed
- Form resets for next zone (on success)
- User sees "Remember to restart service" message

---

## JavaScript Architecture

### Core Utilities (base.html)

All utility functions are defined in the base template:

```javascript
showAlert(message, type, duration)
  // Display alert: success, error, info
  
apiRequest(url, options)
  // Make API request with error handling
  
setFormDisabled(disabled)
  // Disable/enable all form inputs
  
setButtonLoading(button, isLoading)
  // Show loading state on button
  
formatZoneType(name, description)
  // Format zone type display string
```

### Page-Specific Logic (admin.html)

The admin page implements:

```javascript
initPage()
  // Initialize on page load
  // Load cameras, presets from API
  
populateZoneTypeDropdown()
  // Create option elements from ZONE_PRESETS
  
populateCameraDropdown()
  // Create option elements from cameras list
  
handleZoneTypeChange()
  // Update description when zone type selected
  
updateConfigPreview()
  // Update preview section in real-time
  
Form Submit Handler
  // Validate, submit to POST /zones, show result
```

### Event Handlers

```
DOMContentLoaded
  └─> initPage()

#zoneTypeSelect onChange
  └─> handleZoneTypeChange()
  └─> updateConfigPreview()

#cameraSelect onChange
  └─> updateConfigPreview()

#zoneForm onSubmit
  └─> Validate inputs
  └─> Show loading state
  └─> POST /zones
  └─> Show result (success/error)
  └─> Reset form (on success)
```

---

## Styling System

### CSS Architecture

- **Minimal CSS** (~300 lines, no framework)
- **CSS Grid/Flexbox** for layout
- **CSS Variables** for colors and spacing
- **Responsive Design** with media queries
- **Accessibility** support (focus states, reduced motion)

### Color Scheme

- **Primary:** `#667eea` (purple)
- **Primary Dark:** `#764ba2` (darker purple)
- **Success:** `#48bb78` (green)
- **Error:** `#e53e3e` (red)
- **Text:** `#2d3748` (dark gray)
- **Muted:** `#718096` (medium gray)

### Responsive Breakpoints

- **Desktop:** Full layout (600px+)
- **Mobile:** Stacked layout (<600px)
- **Print:** Hides buttons, simplifies display

---

## Extensibility

### Add a New Zone Type

**In `src/config_manager/presets.py`:**

```python
ZONE_PRESETS = {
    "Custom Hazard": {
        "description": "Your custom description",
        "required_ppe": ["hard_hat", "custom_ppe"],
        "alert_cooldown_seconds": 25,
    },
    # ... other zones
}
```

**The UI automatically includes it** — No code changes needed!

### Customize Styling

**CSS file:** `src/api/static/css/style.css`

- Colors defined at top of file
- Layout uses standard flexbox/grid
- Responsive queries at bottom
- Easy to customize or extend

### Add Form Fields

**In `src/api/templates/admin.html`:**

1. Add new `<div class="form-section">` with input
2. Add handler in JavaScript to populate/validate
3. Update `updateConfigPreview()` to include new field

### Add New Preset Information

**To show additional preset fields:**

1. Update `ZONE_PRESETS` structure in `presets.py`
2. Update `GET /zone-presets` response (no change needed)
3. In `admin.html`, update `handleZoneTypeChange()` to display new fields

---

## Error Handling

### Common Errors (Web UI)

| Error | Cause | Solution |
|-------|-------|----------|
| "No cameras found" | No cameras in `cameras.yaml` | Configure cameras first |
| "Zone type not found" | Invalid preset name | Select valid preset from dropdown |
| "Configuration file error" | YAML parsing failed | Check zone YAML syntax |
| "Failed to load page data" | API connection error | Ensure service is running |

### Common Errors (API)

| Status | Error | Cause |
|--------|-------|-------|
| 400 | Camera not found | Invalid camera_id parameter |
| 400 | Zone type not found | Invalid zone_type parameter |
| 500 | Configuration error | YAML/file I/O error |
| 500 | Internal server error | Unexpected error |

---

## Performance Considerations

### Browser Performance
- No external JavaScript libraries (reduce load time)
- CSS animations use GPU-efficient properties
- Minimal DOM manipulation
- Event delegation where possible

### Network Performance
- API responses are JSON (lightweight)
- No large file transfers
- Requests debounced on form changes
- Streaming MJPEG handled separately

### Server Performance
- Template rendering minimal (cached by FastAPI)
- Static files served efficiently (StaticFiles)
- Zone creation is single database write
- No polling or continuous requests

---

## Security Considerations

### Input Validation
- Camera ID validated against cameras.yaml
- Zone type validated against ZONE_PRESETS
- Zone ID auto-generated (no user input)
- All strings escaped in templates

### CORS
- Enabled for `*` (same as existing system)
- Adjust in production: `allow_origins=["https://yourdomain.com"]`

### HTTPS
- Deploy with HTTPS in production
- Update browser to use `https://` URLs
- FastAPI requires reverse proxy (nginx) for HTTPS

---

## Deployment

### Local Development

```bash
# Terminal 1: Start service
python -m uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2: Open browser
# http://localhost:8000/admin
```

### Production Deployment

```bash
# Using Gunicorn + Uvicorn workers
pip install gunicorn
gunicorn src.api.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --host 0.0.0.0 \
  --port 8000

# Behind Nginx reverse proxy (with SSL)
# See deployment guide for configuration
```

---

## Troubleshooting

### "Cannot find module: src.api.main"
- Ensure working directory is project root
- Run: `python -m uvicorn src.api.main:app`

### "Templates not found"
- Check `src/api/templates/` directory exists
- Verify file paths are correct
- Run from project root directory

### "Static files not loading" (404 on CSS)
- Check `src/api/static/css/style.css` exists
- Verify static file mounting code in `main.py`
- Check browser dev console for actual 404 path

### "POST /zones returns 500"
- Check `config/cameras.yaml` is valid YAML
- Check `config/zones.yaml` is valid YAML
- Verify camera_id matches exactly (case-sensitive)
- Check file permissions (can write to config/)

### "Zone created but not enforced"
- **IMPORTANT:** Service must be **restarted** after zone creation
- Check service logs: `tail -f logs/app.log`
- Verify new zone appears in `config/zones.yaml`
- Verify camera_id in zone matches running camera

---

## Future Enhancements

### Phase 2: Zone Management UI
- List existing zones
- Edit zone configuration
- Delete zones
- Enable/disable zones

### Phase 3: Advanced Features
- Bulk zone creation
- Import/export zone configs
- Zone templates library
- Zone scheduling (e.g., different rules at night)

### Phase 4: Analytics Dashboard
- Violations per zone
- Trend analysis
- Most common violations
- Zone effectiveness reports

### Phase 5: Real-Time Visualization
- Draw zones on video frames
- Highlight violations in real-time
- Live person tracking overlay
- Activity heatmaps

---

## Summary

The **Web UI** provides:

✅ **Non-Technical Access** — No CLI or YAML editing required  
✅ **Real-Time Feedback** — Immediate validation and preview  
✅ **API-Driven** — Extensible via REST endpoints  
✅ **Minimal Dependencies** — Fast loading, no build tools  
✅ **Mobile-Friendly** — Responsive design  
✅ **Well-Documented** — Extensive inline comments  
✅ **Production-Ready** — Error handling, validation, logging  

**Files Created:**
- `src/api/templates/base.html` — Base template + utilities
- `src/api/templates/admin.html` — Zone configuration page
- `src/api/static/css/style.css` — Minimal styling

**FastAPI Endpoints Added:**
- `GET /admin` — Serve web UI
- `GET /zone-presets` — Get zone type options
- `POST /zones` — Create new zone

**Integration Points:**
- Uses existing `GET /cameras` endpoint
- Calls config_manager functions for zone creation
- Saves to `config/zones.yaml`
