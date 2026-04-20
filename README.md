# Inspection AI — PPE Compliance System

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.8%2B-brightgreen.svg)
![Status](https://img.shields.io/badge/status-active-success.svg)

An AI-enabled CCTV system for real-time Personal Protective Equipment (PPE) compliance monitoring in high-risk operational areas. Using YOLOv8 object detection and FastAPI, this system provides automated monitoring with zone-specific PPE requirements.

## 📋 Table of Contents

- [Features](#features)
- [Quick Start](#quick-start)
- [Project Structure](#project-structure)
- [Configuration](#configuration)
- [Usage](#usage)
- [API Documentation](#api-documentation)
- [Contributing](#contributing)
- [License](#license)

## ✨ Features

- **Real-time Detection**: RTSP/MJPEG stream processing with configurable FPS limits
- **PPE Recognition**: Detects persons, helmets, vests, gloves, and other safety equipment
- **Zone-based Rules**: Different PPE requirements per surveillance zone
- **Evidence Storage**: Automatic capture and annotation of compliance violations
- **REST API**: FastAPI-based API for integration with other systems
- **Database Tracking**: SQLite database with violation history and metrics
- **Multi-camera Support**: Monitor multiple camera feeds simultaneously
- **Auto-reconnection**: Handles stream failures and reconnects gracefully

## 🚀 Quick Start

### Prerequisites

- Python 3.8 or higher
- NVIDIA GPU recommended (for faster inference)
- 8GB+ RAM

### Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/Abahchevy/inspection-ai.git
   cd inspection-ai
   ```

2. **Create a virtual environment**:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate  # Windows
   # or: source .venv/bin/activate  # Linux/Mac
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Download models** (optional if you want to use pre-trained models):
   ```bash
   python download_model.py
   ```

### Running the System

**Webcam Test** (quick validation):
```bash
python test_webcam.py
```

**With RTSP Streams** (production):
1. Configure cameras in `config/cameras.yaml`
2. Define zone rules in `config/zones.yaml`
3. Start the system:
   ```bash
   python run.py
   ```

**API Server**:
```bash
python -m uvicorn src.api.main:app --reload
```
Access API docs at http://localhost:8000/docs

## 📁 Project Structure

```
inspection-ai/
├── src/
│   ├── api/              # FastAPI endpoints
│   ├── database/         # SQLAlchemy models & session
│   ├── detection/        # YOLOv8 detector & zone rules
│   ├── evidence/         # Frame annotation & storage
│   └── ingestion/        # RTSP stream processor
├── config/
│   ├── cameras.yaml      # Camera stream configuration
│   └── zones.yaml        # Zone-based PPE rules
├── training/             # Model training pipeline
├── models/               # Trained model files (.pt)
├── test_*.py             # Test scripts
└── requirements.txt      # Python dependencies
```

## ⚙️ Configuration

### `config/cameras.yaml`
Define your camera streams:
```yaml
cameras:
  - id: "cam-main"
    source: "rtsp://ip:port/stream"
    fps_limit: 5
    enabled: true
```

### `config/zones.yaml`
Define PPE requirements per zone:
```yaml
zones:
  - id: "high-hazard"
    required_ppe: ["helmet", "vest", "gloves"]
    alert_on_violation: true
```

## 🧪 Testing

Run the test suite:
```bash
# Test detection on video file
python test_detection.py

# Test with webcam
python test_webcam.py
```

## 📡 API Documentation

Once the API is running, visit **http://localhost:8000/docs** for interactive API documentation.

### Key Endpoints

- `GET /health` - System health check
- `GET /cameras` - List configured cameras
- `GET /violations` - Recent PPE violations
- `GET /stats` - System statistics
- `POST /config/reload` - Reload configuration

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on:
- How to set up a development environment
- Code style and conventions
- Pull request process
- Areas where we need help

### Quick contribution ideas:
- Improve detection accuracy
- Add new monitoring features
- Optimize performance
- Enhance documentation
- Create UI/dashboard

## 📝 License

This project is licensed under the MIT License — see [LICENSE](LICENSE) file for details.

## 📧 Contact & Support

For questions, issues, or discussions:
- Open an [Issue](https://github.com/Abahchevy/inspection-ai/issues)
- Check [DOCUMENTATION.md](DOCUMENTATION.md) for technical details

---

**Developed by Abahchevy** | PPE Compliance for Oil & Gas Remote Sites
