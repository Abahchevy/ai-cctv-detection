# Live Camera Preview Implementation

## Overview
The web UI now displays **live camera previews** directly in the browser when a user opens `http://localhost:8000/admin`. This enables end users to visually confirm that cameras are working before committing to zone configuration.

## What Was Implemented

### 1. **Live Preview Section** (admin.html)
Added a new preview section that appears BEFORE the zone configuration form, guiding users through this workflow:
1. **Select camera** → 
2. **See live preview** (instant visual feedback) → 
3. **Verify camera positioning** → 
4. **Configure zone with confidence**

**Key Features:**
- **Loading State**: Animated spinner text while connecting to the MJPEG stream
- **Active Stream**: Displays live MJPEG video from `/stream/{camera_id}`
- **Error Handling**: Shows troubleshooting tips if stream fails to connect
- **Retry Button**: Allows users to reconnect without page reload
- **Status Indicator**: "● Live" badge shows stream is active

### 2. **Enhanced JavaScript** (admin.html)
Added comprehensive stream management functions:

| Function | Purpose |
|----------|---------|
| `handleCameraChange()` | Updates config preview AND live stream when camera selected |
| `updateCameraStream(cameraId)` | Connects to MJPEG endpoint and updates img src |
| `onStreamLoaded()` | Called when first frame arrives; shows video, hides spinner |
| `onStreamError()` | Called if stream fails; displays error + troubleshooting tips |
| `retryStream()` | User clicks retry button to reconnect |
| `stopCameraStream()` | Cleanup when camera deselected or form reset |

**How It Works (MJPEG over <img>):**
```javascript
// Browser continues to fetch JPEG frames from MJPEG stream
// Updates image on every new frame
const streamUrl = `/stream/${encodeURIComponent(cameraId)}`;
streamEl.src = streamUrl;  // This triggers the MJPEG stream
```

### 3. **Responsive CSS Styling** (style.css)
Added comprehensive styles organized into sections:

| Section | Purpose |
|---------|---------|
| `.preview-section` | Container for entire preview + header |
| `.preview-container` | Holds video/loading/error; 16:9 aspect ratio |
| `.spinner` | Animated loading indicator (CSS animation) |
| `.preview-error` | Error message with troubleshooting steps |
| `.stream-status` | "● Live" badge and camera info |
| `.btn-retry` | Styled retry button |
| `@media (max-width: 600px)` | Mobile responsive (4:3 aspect ratio) |

**Key Design Decisions:**
- **16:9 Aspect Ratio**: Standard video format, scalable on all screens
- **Dark Background** (`#1a202c`): Provides contrast for video display
- **Status Badge**: Clear visual indicator when stream is live
- **Centered Layout**: Using flexbox for consistent centering
- **Smooth Transitions**: 0.3s easing on all interactive elements

### 4. **MJPEG Streaming Performance** (main.py - already optimized)
The `/stream/{camera_id}` endpoint (lines 432-453) already includes:
- **Frame Rate**: ~25 fps (via `await asyncio.sleep(0.04)`)
- **JPEG Quality**: 80/100 (balance between quality and bandwidth)
- **Error Handling**: 404 if camera not running
- **Loop Management**: Continuous frame fetch from `_latest_frames` dict

## How It Integrates with Existing System

### Data Flow:
```
User Opens /admin
└─ Load cameras from GET /cameras
└─ Populate camera dropdown
└─ User selects camera
   └─ handleCameraChange() called
      ├─ Update config preview
      └─ Call updateCameraStream(cameraId)
         └─ <img src> = "/stream/{camera_id}"
            └─ Browser fetches MJPEG frames
               └─ Stream connected!
```

### Component Integration:
- **FastAPI Backend** (main.py): 
  - Already has `/stream/{camera_id}` MJPEG endpoint
  - Updated `/cameras` endpoint used to populate dropdown
  - Zone creation remains same (POST `/zones`)

- **Frontend** (admin.html + style.css):
  - New preview section with stream handling
  - Camera change event triggers stream update
  - Form validation unchanged

- **Streaming** (existing StreamProcessor):
  - Continues processing frames in background
  - Latest annotated frames stored in `_latest_frames` dict
  - Available to MJPEG endpoint in real-time

## User Experience Flow

### Happy Path:
```
1. User opens http://localhost:8000/admin
2. Page loads cameras and zone presets
3. User selects camera from dropdown
4. Loading spinner appears
5. Within 1-2 seconds, live video appears
6. User sees real-time movement in camera preview
7. User selects zone type and creates zone
8. Success! ✨
```

### Error Path:
```
1. User selects camera
2. Loading spinner appears
3. After 4-5 seconds, stream fails to load
4. Error message appears with troubleshooting tips:
   - Ensure service is running: `python -m src.api.main`
   - Verify camera enabled in config/cameras.yaml
   - Check service logs
   - Try restarting service
5. User clicks "🔄 Retry Connection" button
6. Stream reconnects (if issue resolved)
```

## Testing Checklist

- [ ] Start the FastAPI server: `python -m src.api.main`
- [ ] Open `http://localhost:8000/admin` in browser
- [ ] Verify page loads without errors
- [ ] Camera dropdown populates with available cameras
- [ ] Select a camera:
  - [ ] Loading spinner appears
  - [ ] Within 1-2 seconds, live video appears
  - [ ] See "● Live" status indicator
- [ ] If camera is running (with webcam or RTSP stream):
  - [ ] Move in front of camera
  - [ ] Verify movement appears in preview
- [ ] Switch to different camera:
  - [ ] Video preview updates instantly (no page reload)
  - [ ] Status stays "● Live" or shows error if not running
- [ ] Test error path (disable/stop camera):
  - [ ] Select stopped camera
  - [ ] Error message appears with troubleshooting tips
  - [ ] Click "🔄 Retry Connection" button
  - [ ] Stream reconnects when camera restarts
- [ ] Select zone type and create zone:
  - [ ] Zone creation still works as before
  - [ ] Success message displays
  - [ ] Prompt to restart service appears

## Performance & Safety Notes

### Frame Throttling:
- MJPEG endpoint limited to ~25 fps (adequate for preview)
- JPEG quality set to 80 (good balance for bandwidth)
- Backend frame update in `_latest_frames` dict (O(1) lookup)

### Memory Safety:
- `_latest_frames` dict holds only current frame per camera (not buffered)
- MJPEG generator doesn't buffer frames, streams directly
- `await asyncio.sleep(0.04)` prevents CPU spinning

### Browser Safety:
- MJPEG URL is built with `encodeURIComponent()` (prevents injection)
- Error messages don't trust user input
- Image onload/onerror handlers properly scoped

## API Reference

### GET /stream/{camera_id}
**Purpose:** Stream live MJPEG video from camera

**Response:**
- Content-Type: `multipart/x-mixed-replace; boundary=frame`
- Each chunk is a complete JPEG image
- Runs at ~25 fps

**Error Responses:**
- 404: Camera not running or doesn't exist
- 500: Streaming error (backend logs provide details)

### Example Usage:
```html
<!-- Browser automatically handles MJPEG format -->
<img src="/stream/cam-001" alt="Live Camera" />
```

## Comments & Documentation

All new code includes comprehensive comments explaining:
- **What** it does (clear function/section name)
- **Why** it exists (purpose and user benefit)
- **How** it works (technical details)
- **Where** it integrates (data flow and dependencies)

Example from admin.html:
```javascript
/**
 * Update the live camera stream
 *
 * How it works:
 * 1. Build stream URL: /stream/{camera_id}
 * 2. Point the <img> element to that URL
 * 3. Browser handles the MJPEG stream automatically
 * 4. Show loading spinner until first frame arrives (onload callback)
 * 5. If stream fails to load (onerror callback), show error message
 *
 * Why MJPEG works with <img>:
 * - MJPEG is a series of JPEG frames sent with HTTP boundary markers
 * - Browsers support this natively via img elements
 * - When new frame arrives, browser updates the image automatically
 * - Much simpler than video tag or canvas rendering
 *
 * @param {string} cameraId - Camera ID to stream from
 */
function updateCameraStream(cameraId) {
    // ...
}
```

## Future Enhancements (Out of Scope)

These could be added later if needed:
- [ ] Video recording capability during preview
- [ ] Frame rate / resolution selection
- [ ] Snapshot capture for documentation
- [ ] Fullscreen preview mode
- [ ] Multiple camera grid view
- [ ] WebSocket-based stream (lower latency)
- [ ] H.264 stream option (lower bandwidth)

## Files Modified

1. **src/api/templates/admin.html**
   - Added `.preview-section` with live camera preview
   - Added stream handling JavaScript functions
   - Added comprehensive code comments

2. **src/api/static/css/style.css**
   - Added `.preview-section` and related styles
   - Added `.preview-container` with aspect ratio
   - Added `.spinner` animation
   - Added `.preview-error` and `.btn-retry` styles
   - Enhanced mobile responsiveness
   - Added 700px max-width for layout
   - Added extensive inline documentation

3. **src/api/main.py** (no changes needed)
   - `/stream/{camera_id}` endpoint already optimized
   - Frame throttling: ~25 fps via `asyncio.sleep(0.04)`
   - JPEG quality: 80/100

## Deployment Notes

- No database migrations needed
- No dependencies added (uses existing OpenCV, FastAPI, etc.)
- No configuration changes required
- Works with all existing camera configurations
- Compatible with both webcam and RTSP streams
