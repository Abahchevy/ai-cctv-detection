# Custom PPE Model Training Pipeline

**Status:** ISOLATED - Not yet integrated with main application

This folder contains tools to collect, label, and train a custom YOLOv8 model for PPE detection.

## Folder Structure

```
training/
├── training_pipeline.py      # Main training script
├── data_template.yaml        # Dataset configuration template
├── README.md                 # This file
├── raw_images/              # (Created during data collection)
├── dataset/                 # (Created after labeling)
│   ├── images/
│   │   ├── train/
│   │   └── val/
│   ├── labels/
│   │   ├── train/
│   │   └── val/
│   └── data.yaml           # Your custom data.yaml
└── runs/                    # (Created after training)
    └── detect/
        └── train/
            └── weights/
                ├── best.pt          # Best model
                └── last.pt          # Last checkpoint
```

## Quick Start

### Step 1: Collect Field Data
Capture images from your webcam/cameras for labeling:

```powershell
cd C:\Users\linab\Desktop\inspection-ai\training
python training_pipeline.py collect
```

**Instructions:**
- Point camera at workers with/without PPE
- Press **'s'** to save each frame
- Press **'q'** to quit when done (~200+ images recommended)
- Images saved to `raw_images/`

---

### Step 2: Label Your Data

**Choose one tool:**

#### Option A: CVAT (Self-hosted, Professional)
1. Go to https://www.cvat.ai/
2. Create project with detection task
3. Upload images from `raw_images/`
4. Label objects (hard_hat, safety_vest, etc.)
5. Export in YOLO format

#### Option B: Roboflow (Easy, Web-based)
1. Go to https://roboflow.com/
2. Create new project
3. Upload images
4. Label with Roboflow's annotation tool
5. Export as YOLO format
6. Download zip file

#### Option C: LabelImg (Local, Simple)
1. Download: https://github.com/heartexlabs/labelImg
2. Open `raw_images/` directory
3. Draw bounding boxes on each image
4. Export as YOLO format

**Expected Output:**
```
dataset/
├── images/
│   ├── train/     (80% of images)
│   │   ├── img_001.jpg
│   │   ├── img_002.jpg
│   │   └── ...
│   └── val/       (20% of images)
│       ├── img_101.jpg
│       └── ...
└── labels/
    ├── train/     (txt files, one per image)
    │   ├── img_001.txt
    │   └── ...
    └── val/
        ├── img_101.txt
        └── ...
```

**YOLO Label Format (each txt file):**
```
<class_id> <x_center_norm> <y_center_norm> <width_norm> <height_norm>
```

Example (hard_hat class 0, centered at 50%, size 30%x40%):
```
0 0.5 0.5 0.3 0.4
```

---

### Step 3: Create Dataset Configuration

1. Copy `data_template.yaml` to `dataset/data.yaml`
2. Update class names to match your labels:

```yaml
path: C:/Users/linab/Desktop/inspection-ai/training/dataset
train: images/train
val: images/val

nc: 3
names:
  0: hard_hat
  1: safety_vest
  2: safety_gloves
  # Add more classes as needed
```

---

### Step 4: Train the Model

```powershell
python training_pipeline.py train
```

**What happens:**
- Downloads YOLOv8m base model (~50 MB)
- Trains on your labeled images (100 epochs default)
- Saves best model to `runs/detect/train/weights/best.pt`
- Training time: 30 min - 2 hours (CPU), 5-10 min (GPU)

**To use GPU (faster):**
Edit `training_pipeline.py` line ~130:
```python
device="cuda"  # instead of "cpu"
```

---

### Step 5: Evaluate Performance

```powershell
python training_pipeline.py eval
```

**Output metrics:**
- **mAP50:** Mean Average Precision at 50% IoU
- **mAP50-95:** Mean Average Precision across IoU thresholds

**Good scores:**
- mAP50 > 0.70 ✓ Ready for deployment
- mAP50 0.50-0.70 ⚠ Acceptable, may need more data
- mAP50 < 0.50 ✗ Needs more training data or labels

---

### Step 6: Deploy to Main App

```powershell
python training_pipeline.py deploy
```

**Manual integration steps:**

1. **Update main app config:**
   
   Edit `../config/cameras.yaml`:
   ```yaml
   model:
     path: "models/best_custom.pt"  # Point to your model
     confidence: 0.40
   ```

2. **Update class mappings:**
   
   Edit `../config/zones.yaml`:
   ```yaml
   class_map:
     "hard_hat": hard_hat
     "safety_vest": safety_vest
     "safety_gloves": safety_gloves
     "person": person
   ```

3. **Update zone requirements:**
   
   Edit `../config/zones.yaml` zones section:
   ```yaml
   zones:
     zone-entry:
       name: "Entry Area"
       required_ppe:
         - hard_hat
         - safety_vest
       alert_cooldown_seconds: 30
   ```

4. **Restart main server:**
   ```powershell
   # Kill the old server
   # Then start new one
   python ../run.py
   ```

---

## Troubleshooting

### "No detections in training"
- Increase training data (aim for 200+ images per class)
- Check image quality (well-lit, clear objects)
- Lower `confidence` threshold in cameras.yaml (try 0.25)

### "Poor mAP scores"
- Add more diverse images (different angles, lighting, people)
- Check labeling accuracy (watch for mislabeled images)
- Increase epochs (try 200-300)

### "Out of memory during training"
- Reduce batch size in training_pipeline.py (line ~115)
- Use smaller model: `yolov8s.pt` instead of `yolov8m.pt`

### "Model overfitting (train loss low, val loss high)"
- Add more training data
- Enable augmentation (already enabled in script)
- Reduce model size

---

## Data Collection Tips

**For best results:**
- ✓ Capture in your actual working environment
- ✓ Include people with PPE + without PPE
- ✓ Vary angles, distances, lighting
- ✓ Include partial views (people in/out of frame)
- ✗ Avoid low-light or blurry images
- ✗ Don't over-represent one person/angle

---

## Class Definition

Customize based on your `zones.yaml`:

```yaml
# Suggested classes
classes:
  0: hard_hat          # Required in most zones
  1: safety_vest       # High-risk areas
  2: safety_glasses    # Lab/chemical areas
  3: gloves            # Lab/chemical areas
  4: safety_boots      # General requirement
  5: respirator        # Hazardous areas
  6: welding_helmet    # Welding areas
  7: protective_suit   # Chemical areas
```

---

## Integration Checklist

Before deploying trained model:

- [ ] Collected 200+ images
- [ ] Labeled all images in YOLO format
- [ ] Created `dataset/data.yaml`
- [ ] Trained model (mAP50 > 0.70)
- [ ] Evaluated on validation set
- [ ] Copied `best.pt` to models folder
- [ ] Updated `cameras.yaml` model path
- [ ] Updated `zones.yaml` class_map
- [ ] Updated `zones.yaml` zone requirements
- [ ] Tested on live feed before full deployment

---

## References

- **YOLOv8 Docs:** https://docs.ultralytics.com/
- **CVAT Tutorials:** https://www.cvat.ai/docs/
- **Roboflow Tutorials:** https://roboflow.com/
- **YOLO Format Guide:** https://docs.ultralytics.com/datasets/detect/

---

**Ready to start?**

```powershell
cd C:\Users\linab\Desktop\inspection-ai\training
python training_pipeline.py collect
```

After collecting images, follow Step 2-6 above!
