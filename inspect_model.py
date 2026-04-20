"""
Inspect the YOLOv8 model to see what it's actually trained on
"""
from ultralytics import YOLO
from pathlib import Path

model_path = "models/best.pt"

if not Path(model_path).exists():
    print(f"ERROR: {model_path} not found!")
    exit(1)

print(f"Loading model: {model_path}\n")
model = YOLO(model_path)

print("=" * 60)
print("MODEL INFORMATION")
print("=" * 60)
print(f"Model name: {model.model.model_info()}")
print(f"\nAvailable classes: {model.names}")
print(f"Number of classes: {len(model.names)}")

print("\n" + "=" * 60)
print("DETECTED CLASSES:")
print("=" * 60)
for class_id, class_name in model.names.items():
    print(f"  {class_id}: {class_name}")

print("\n" + "=" * 60)
print("INFERENCE TEST")
print("=" * 60)

# Try inference on a blank image
import numpy as np
dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)

print("Running inference on blank image...")
results = model(dummy_frame, conf=0.1, verbose=False)
if results:
    result = results[0]
    print(f"Result boxes: {result.boxes}")
    print(f"Detection count: {len(result.boxes) if result.boxes else 0}")

print("\nTry pointing your webcam at this script output and see if detection works.")
print("If classes don't include 'helmet' or 'person', the model is not a hard-hat detection model!")
