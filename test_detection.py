"""
Quick test script to debug model detection on webcam
Run with: python test_detection.py
Press 'q' to quit
"""
import cv2
from src.detection.detector import PPEDetector
import yaml
from pathlib import Path

# Load config
cameras_cfg = yaml.safe_load(Path("config/cameras.yaml").read_text())
zones_cfg = yaml.safe_load(Path("config/zones.yaml").read_text())

# Initialize detector with current config
model_cfg = cameras_cfg.get("model", {})
detector = PPEDetector(
    model_path=model_cfg.get("path", "models/best.pt"),
    class_map=zones_cfg.get("class_map", {}),
    confidence_threshold=float(model_cfg.get("confidence", 0.25)),
    device=str(model_cfg.get("device", "cpu")),
    enable_tracking=bool(model_cfg.get("enable_tracking", False)),
)

print(f"✓ Model loaded: {model_cfg.get('path')}")
print(f"✓ Confidence threshold: {model_cfg.get('confidence', 0.25)}")
print(f"✓ Device: {model_cfg.get('device', 'cpu')}")
print(f"✓ Class map: {zones_cfg.get('class_map', {})}")
print("\nOpening webcam... (press 'q' to quit)\n")

# Open webcam
cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
if not cap.isOpened():
    print("ERROR: Cannot open webcam!")
    exit(1)

frame_count = 0
while True:
    ret, frame = cap.read()
    if not ret:
        print("Frame read failed!")
        break
    
    frame_count += 1
    
    # Run detection
    detections, persons = detector.process_frame(frame)
    
    # Print results every 10 frames
    if frame_count % 10 == 0:
        print(f"\n--- Frame {frame_count} ---")
        if detections:
            print(f"Total detections: {len(detections)}")
            for det in detections:
                print(f"  • {det.class_name} (conf={det.confidence:.2f}, ppe_id={det.ppe_id})")
        else:
            print("⚠ NO DETECTIONS! Check lighting/angle or lower confidence further.")
        
        print(f"Persons detected: {len(persons)}")
        for i, person in enumerate(persons):
            print(f"  • Person {i}: worn_ppe={person.worn_ppe}, missing={person.missing_ppe(set(['hard_hat']))}")
    
    # Display
    small = cv2.resize(frame, (640, 480))
    cv2.imshow("Webcam Test", small)
    
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
print("\nTest complete!")
