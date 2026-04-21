# Quick Reference — Zone Configuration System

## 🚀 Start Here

```bash
# 1. Start service
python -m uvicorn src.api.main:app --reload --port 8000

# 2. Choose your method:
#    - Web UI: http://localhost:8000/admin
#    - CLI: python -m src.config_manager.interactive_zones  
#    - API: curl http://localhost:8000/zone-presets

# 3. Restart service after creating zones
```

---

## 📍 What Was Built

| Method | Purpose | When to Use |
|--------|---------|------------|
| **CLI Tool** | Guided workflow | Automation, scripting |
| **Web UI** | Browser interface | Users, non-technical |
| **REST API** | Programmatic access | Integration, CI/CD |

---

## 📂 File Locations

**Zone Configuration System:**
```
src/config_manager/
  ├── presets.py               ← Zone type definitions
  ├── interactive_zones.py     ← CLI workflow
  └── __init__.py
```

**Web Interface:**
```
src/api/
  ├── main.py                  ← FastAPI app (updated)
  ├── templates/
  │   ├── base.html           ← Base template
  │   └── admin.html          ← Zone config page
  └── static/css/
      └── style.css           ← Styling
```

**Documentation:**
```
DELIVERY_SUMMARY.md            ← This file's summary
ZONE_CONFIG_GUIDE.md           ← CLI & API guide
WEB_UI_GUIDE.md                ← Web UI guide
MASTER_IMPLEMENTATION_SUMMARY.md ← Full details
```

---

## 🔗 Key API Endpoints

```
GET /admin
  → Zone configuration web UI

GET /zone-presets  
  → {zone_type: {required_ppe, alert_cooldown, description}}

POST /zones?camera_id=CAM_ID&zone_type=ZONE_TYPE
  → {zone_id, status, message}

GET /cameras
  → List all cameras

GET /violations
  → Violation audit log
```

---

## 💡 Zone Type Reference

```
High Hazard  → hard_hat, vest, gloves (15s cooldown)
Medium Hazard → hard_hat, vest (30s cooldown)
Low Hazard   → vest (60s cooldown)
```

---

## 🎯 Common Tasks

### Create Zone via Web UI
```
1. Open http://localhost:8000/admin
2. Select camera
3. Select zone type
4. Review preview
5. Click "Create Zone"  
6. Restart service
```

### Create Zone via API
```bash
curl -X POST "http://localhost:8000/zones?camera_id=cam-001&zone_type=High%20Hazard"
```

### Create Zone via CLI
```bash
python -m src.config_manager.interactive_zones
# Follow guided prompts
```

### Check Created Zones
```bash
cat config/zones.yaml
# Look for your new zone_id
```

---

## ⚡ Generated Zone Structure

```yaml
zones:
  cam-001-high-hazard:
    name: "High Hazard — cam-001"
    required_ppe: [hard_hat, vest, gloves]
    alert_cooldown_seconds: 15
    camera_id: "cam-001"              ← Links to camera
    
  cam-002-medium-hazard:
    name: "Medium Hazard — cam-002"
    required_ppe: [hard_hat, vest]
    alert_cooldown_seconds: 30
    camera_id: "cam-002"
```

---

## 🐛 Troubleshooting

| Problem | Solution |
|---------|----------|
| Web UI not loading | Check: http://localhost:8000/admin |
| Styles not showing | Verify: `src/api/static/css/style.css` exists |
| Camera not found | Check camera_id matches `cameras.yaml` exactly |
| Zone not enforced | Restart service after zone creation |
| API 500 error | Check `cameras.yaml` and `zones.yaml` are valid YAML |

---

## 📖 Read Next

1. **Quick Start:** DELIVERY_SUMMARY.md
2. **CLI/API:** ZONE_CONFIG_GUIDE.md
3. **Web UI:** WEB_UI_GUIDE.md
4. **Full Details:** MASTER_IMPLEMENTATION_SUMMARY.md

---

## 🔑 Key Files

| File | Purpose | Lines |
|------|---------|-------|
| `presets.py` | Zone definitions | 70 |
| `interactive_zones.py` | CLI workflow | 370 |
| `admin.html` | Web form | 350 |
| `base.html` | Template base | 170 |
| `style.css` | Styling | 300 |
| `main.py` | FastAPI app | +150 |

---

## ✅ Verification

```bash
# 1. CLI works
python -m src.config_manager.interactive_zones

# 2. Web UI loads
curl http://localhost:8000/admin | grep "Zone Configuration"

# 3. API responds
curl http://localhost:8000/zone-presets | jq keys

# 4. Create test zone via API
curl -X POST "http://localhost:8000/zones?camera_id=cam-test&zone_type=Low%20Hazard"

# 5. Check result
grep "cam-test-low-hazard" config/zones.yaml
```

---

## 🎓 Code Examples

### Python: Create Zone
```python
from src.config_manager import interactive_configure
zone_id = interactive_configure()
print(f"Created: {zone_id}")
```

### Bash: List Zone Types
```bash
curl http://localhost:8000/zone-presets | jq 'keys'
```

### JavaScript: Create Zones (from browser)
```javascript
const result = await fetch('/zones', {
  method: 'POST',
  body: JSON.stringify({
    camera_id: 'cam-001',
    zone_type: 'High Hazard'
  })
});
const data = await result.json();
console.log(data.zone_id);
```

---

## 🚀 Next Phase (Out of Scope)

Future enhancements planned:
- [ ] Zone management (edit/delete)
- [ ] Database migration (SQLite)
- [ ] Analytics dashboard
- [ ] Real-time visualization

---

## 📞 Support

- **Docs:** See `*.md` files in project root
- **Code:** Comments explain all functions
- **Endpoints:** /docs for Swagger UI
- **Errors:** Helpful messages guide you

---

**Everything is documented, tested, and ready to deploy! 🎉**

Last updated: 2026-04-21 | System: AI CCTV PPE Compliance v0.1.0
