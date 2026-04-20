"""
TRAINING PIPELINE FOR CUSTOM PPE DETECTION MODEL
==================================================

This guide walks you through:
1. Collecting field data (images from your cameras)
2. Labeling with CVAT or Roboflow
3. Training YOLOv8 on custom data
4. Evaluating and deploying the model
"""

# ===================================================================
# STEP 1: COLLECT FIELD DATA
# ===================================================================

# This script captures frames from your webcam and saves them for labeling

import cv2
import os
from datetime import datetime
from pathlib import Path

def collect_field_data(output_dir: str = "raw_images", num_frames: int = 100):
    """
    Capture images from webcam for training dataset.
    Images will be saved to output_dir.
    Press 's' to save frame, 'q' to quit.
    """
    
    os.makedirs(output_dir, exist_ok=True)
    
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    if not cap.isOpened():
        print("ERROR: Cannot open webcam!")
        return
    
    print(f"Starting field data collection...")
    print(f"Press 's' to save frame, 'q' to quit")
    print(f"Frames will be saved to: {output_dir}\n")
    
    frame_count = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        # Display instructions
        cv2.putText(frame, f"Frames saved: {frame_count}", (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv2.putText(frame, "Press 's' to save, 'q' to quit", (10, 70),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 1)
        
        cv2.imshow("Field Data Collection", frame)
        key = cv2.waitKey(1) & 0xFF
        
        if key == ord('s'):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"frame_{timestamp}_{frame_count:04d}.jpg"
            filepath = os.path.join(output_dir, filename)
            cv2.imwrite(filepath, frame)
            frame_count += 1
            print(f"✓ Saved {filename}")
            
            if frame_count >= num_frames:
                print(f"\nCollected {num_frames} images!")
                break
        
        elif key == ord('q'):
            break
    
    cap.release()
    cv2.destroyAllWindows()
    print(f"Collection complete. {frame_count} images saved to {output_dir}")

# ===================================================================
# STEP 2: LABELING INSTRUCTIONS
# ===================================================================

LABELING_GUIDE = """
DATASET LABELING WORKFLOW
==========================

Tools available:
  1. CVAT (Computer Vision Annotation Tool) - Free, self-hosted
     URL: https://www.cvat.ai/
     
  2. Roboflow - Easy web-based tool
     URL: https://roboflow.com/
     
  3. LabelImg - Local GUI tool
     Download: https://github.com/heartexlabs/labelImg

After labeling, your dataset should be organized as:
```
dataset/
├── images/
│   ├── train/
│   │   ├── img1.jpg
│   │   ├── img2.jpg
│   │   └── ...
│   └── val/
│       ├── img1.jpg
│       └── ...
└── labels/
    ├── train/
    │   ├── img1.txt  (YOLO format: <class> <x_center> <y_center> <width> <height>)
    │   ├── img2.txt
    │   └── ...
    └── val/
        ├── img1.txt
        └── ...
```

YOLO Label Format (TXT files):
<class_id> <x_center_norm> <y_center_norm> <width_norm> <height_norm>

Example for image 640x480 with hard_hat at (320, 240):
  0 0.5 0.5 0.3 0.4
  
Classes (define in data.yaml):
  0: hard_hat
  1: safety_vest
  2: safety_gloves
  ... (define based on your zones.yaml)
"""

# ===================================================================
# STEP 3: DATASET CONFIGURATION
# ===================================================================

DATASET_YAML_TEMPLATE = """
# data.yaml - YOLOv8 dataset configuration
path: {dataset_dir}  # absolute path
train: images/train
val: images/val
test: images/test  # optional

nc: 3  # number of classes
names: ['hard_hat', 'safety_vest', 'safety_gloves']  # class names
"""

# ===================================================================
# STEP 4: TRAINING SCRIPT
# ===================================================================

def train_model(data_yaml: str, model_size: str = "m", epochs: int = 100, device: str = "cpu"):
    """
    Train YOLOv8 model on custom dataset.
    
    Args:
        data_yaml: Path to data.yaml
        model_size: 'n' (nano), 's' (small), 'm' (medium), 'l' (large), 'x' (xlarge)
        epochs: Number of training epochs
        device: 'cpu' or 'cuda'
    """
    from ultralytics import YOLO
    
    print(f"Loading YOLOv8{model_size} base model...")
    model = YOLO(f"yolov8{model_size}.pt")
    
    print(f"Starting training...")
    results = model.train(
        data=data_yaml,
        epochs=epochs,
        imgsz=640,
        device=device,
        patience=20,  # Early stopping
        batch=16,     # Reduce if out of memory
        save=True,
        cache=True,
        workers=4,
        mosaic=1.0,
        flipud=0.5,
        fliplr=0.5,
        translate=0.1,
        scale=0.5,
        hsv_h=0.015,
        hsv_s=0.7,
        hsv_v=0.4,
        degrees=10,
        perspective=0.0,
        shear=0.0,
    )
    
    print(f"\nTraining complete!")
    print(f"Best model saved to: {results.save_dir}/weights/best.pt")
    
    return model, results

# ===================================================================
# STEP 5: EVALUATION & TESTING
# ===================================================================

def evaluate_model(model_path: str, data_yaml: str):
    """Evaluate trained model on validation set."""
    from ultralytics import YOLO
    
    model = YOLO(model_path)
    results = model.val(data=data_yaml)
    
    print(f"\nValidation Results:")
    print(f"  mAP50: {results.box.map50:.3f}")
    print(f"  mAP50-95: {results.box.map:.3f}")
    
    return results

# ===================================================================
# STEP 6: DEPLOY TRAINED MODEL
# ===================================================================

def deploy_model(trained_model_path: str, destination: str = "../models/best_custom.pt"):
    """
    Copy trained model to production and update config.
    """
    import shutil
    
    print(f"Copying {trained_model_path} -> {destination}")
    shutil.copy(trained_model_path, destination)
    
    print("\nTo integrate with main app:")
    print("1. Update ../config/cameras.yaml:")
    print("     model:")
    print("       path: 'models/best_custom.pt'  # Your trained model")
    print("\n2. Update ../config/zones.yaml class_map with your classes:")
    print("     class_map:")
    print("       'hard_hat': hard_hat")
    print("       'safety_vest': safety_vest")
    print("       'safety_gloves': safety_gloves")
    print("\n3. Restart the server!")

# ===================================================================
# QUICK START
# ===================================================================

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print(__doc__)
        print("\nUsage (run from training/ directory):")
        print("  python training_pipeline.py collect    # Collect field data")
        print("  python training_pipeline.py label      # Show labeling instructions")
        print("  python training_pipeline.py train      # Train model (requires labeled data)")
        print("  python training_pipeline.py eval       # Evaluate model")
        print("  python training_pipeline.py deploy     # Deploy to production")
        sys.exit(1)
    
    cmd = sys.argv[1]
    
    if cmd == "collect":
        collect_field_data(num_frames=200)
    
    elif cmd == "label":
        print(LABELING_GUIDE)
        print("\nDataset YAML template:")
        print(DATASET_YAML_TEMPLATE)
    
    elif cmd == "train":
        # Requires: dataset/data.yaml with your labeled data
        model, results = train_model(
            data_yaml="dataset/data.yaml",
            model_size="m",
            epochs=100,
            device="cpu"  # Change to "cuda" if GPU available
        )
    
    elif cmd == "eval":
        evaluate_model(
            model_path="runs/detect/train/weights/best.pt",
            data_yaml="dataset/data.yaml"
        )
    
    elif cmd == "deploy":
        deploy_model("runs/detect/train/weights/best.pt")
    
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)
