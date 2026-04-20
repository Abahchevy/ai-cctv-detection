"""
Load hard-hat detection model directly from Hugging Face using Ultralytics
"""
from ultralytics import YOLO
from pathlib import Path

print("Attempting to load hard-hat detection model from Hugging Face...")
print("This may take a few minutes on first run...\n")

try:
    # Try to load directly from HuggingFace
    model = YOLO("keremberke/yolov8m-hard-hat-detection")
    
    # Save locally
    model_path = Path("models/best.pt")
    model.save(str(model_path))
    
    print(f"✓ Model loaded and saved to: {model_path}")
    print(f"✓ File size: {model_path.stat().st_size / (1024*1024):.1f} MB")
    print(f"\nModel classes:")
    for class_id, class_name in model.names.items():
        print(f"  {class_id}: {class_name}")
    
except Exception as e:
    print(f"✗ ERROR: {e}")
    print(f"\nTrying alternative: loading generic YOLOv8 model...")
    try:
        model = YOLO("yolov8m.pt")  # Generic model
        model.save("models/best.pt")
        print("✓ Generic YOLOv8m model saved")
    except Exception as e2:
        print(f"✗ Also failed: {e2}")
